use std::process::{Command, Child};
use std::sync::Mutex;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::{Duration, Instant};
use std::io::Write;
#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;
use tauri::Manager;

/// 杀死进程及其所有子进程树（Windows: taskkill /F /T, Unix: kill）
#[cfg(target_os = "windows")]
fn kill_process_tree(pid: u32) {
    let _ = Command::new("taskkill")
        .args(["/F", "/T", "/PID", &pid.to_string()])
        .creation_flags(CREATE_NO_WINDOW)
        .status();
}

#[cfg(not(target_os = "windows"))]
fn kill_process_tree(pid: u32) {
    let _ = Command::new("kill").args(["-9", &pid.to_string()]).status();
}

/// Windows CREATE_NO_WINDOW — 不弹出控制台窗口
#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x08000000;

// 桌面端专用导入
#[cfg(desktop)]
use tauri::tray::{TrayIconBuilder, MouseButton, TrayIconEvent};
#[cfg(desktop)]
use tauri::menu::{Menu, MenuItem, PredefinedMenuItem};
use tauri::WebviewUrl;

// 桌面端专用：后端进程管理
#[cfg(desktop)]
struct BackendProcess(Mutex<Option<Child>>);

#[cfg(desktop)]
impl Drop for BackendProcess {
    fn drop(&mut self) {
        if let Ok(mut g) = self.0.lock() {
            if let Some(ref mut c) = *g {
                kill_process_tree(c.id());
                let _ = c.wait();
            }
            *g = None;
        }
    }
}

const CLOCK_LABEL: &str = "clock";
const INPUT_LABEL: &str = "countdown_input";
const TODO_LABEL: &str = "todo_calendar";

/// 防止并发创建日历窗口的锁
#[cfg(desktop)]
static TODO_CREATING: AtomicBool = AtomicBool::new(false);

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! Welcome to AI Nexus Assistant.", name)
}

#[cfg(desktop)]
#[tauri::command]
fn show_main_window(app: tauri::AppHandle) {
    close_clock(&app);
    close_input(&app);
    close_todo(&app);
    if let Some(w) = app.get_webview_window("main") {
        let _ = w.set_skip_taskbar(false);
        let _ = w.show();
        let _ = w.set_focus();
        // Notify frontend that window is visible again
        let _ = w.eval("window.dispatchEvent(new CustomEvent('nexus-window-show'))");
    }
}

#[cfg(desktop)]
#[tauri::command]
fn close_clock_window(app: tauri::AppHandle) {
    close_clock(&app);
}

#[cfg(desktop)]
#[tauri::command]
fn close_input_window(app: tauri::AppHandle) {
    close_input(&app);
}

#[cfg(desktop)]
#[tauri::command]
fn close_todo_window(app: tauri::AppHandle) {
    close_todo(&app);
}

#[cfg(desktop)]
#[tauri::command]
fn set_countdown(app: tauri::AppHandle, minutes: u64) {
    close_input(&app);
    if let Some(cw) = app.get_webview_window(CLOCK_LABEL) {
        let js = format!(
            "(function() {{ window._isCD = true; window._cdDone = false; window._cdTarget = Date.now() + {} * 60000; }})();",
            minutes
        );
        let _ = cw.eval(&js);
    }
}

#[cfg(desktop)]
#[tauri::command]
fn cancel_countdown(app: tauri::AppHandle) {
    if let Some(cw) = app.get_webview_window(CLOCK_LABEL) {
        let _ = cw.eval("(function() { window._isCD = false; window._cdDone = false; })();");
    }
}

#[cfg(desktop)]
#[tauri::command]
fn toggle_bg(app: tauri::AppHandle) {
    if let Some(cw) = app.get_webview_window(CLOCK_LABEL) {
        let _ = cw.eval(r#"
            (function() {
                window._trans = !window._trans;
                document.body.classList.toggle('transparent', window._trans);
            })();
        "#);
    }
}

/// 读取目录中的音频文件列表
#[tauri::command]
fn list_audio_files(dir_path: String) -> Result<Vec<serde_json::Value>, String> {
    let dir = std::path::Path::new(&dir_path);
    if !dir.is_dir() {
        return Err("不是有效目录".into());
    }
    let audio_exts = [".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac"];
    let mut files = Vec::new();
    let entries = std::fs::read_dir(dir).map_err(|e| e.to_string())?;
    for entry in entries {
        let entry = entry.map_err(|e| e.to_string())?;
        let path = entry.path();
        if path.is_file() {
            if let Some(ext) = path.extension() {
                let ext_lower = ext.to_string_lossy().to_lowercase();
                if audio_exts.iter().any(|e| e.trim_start_matches('.') == ext_lower) {
                    let name = path.file_name().unwrap_or_default().to_string_lossy().to_string();
                    let size = entry.metadata().map(|m| m.len()).unwrap_or(0);
                    let mime = match ext_lower.as_str() {
                        "mp3" => "audio/mpeg",
                        "flac" => "audio/flac",
                        "wav" => "audio/wav",
                        "ogg" => "audio/ogg",
                        "m4a" => "audio/mp4",
                        "aac" => "audio/aac",
                        _ => "application/octet-stream",
                    };
                    files.push(serde_json::json!({
                        "name": name,
                        "path": path.to_string_lossy().to_string(),
                        "size": size,
                        "type": mime
                    }));
                }
            }
        }
    }
    files.sort_by(|a, b| {
        a["name"].as_str().unwrap_or("").cmp(b["name"].as_str().unwrap_or(""))
    });
    Ok(files)
}

/// 读取文件内容并返回 base64
#[tauri::command]
fn read_file_base64(file_path: String) -> Result<String, String> {
    let data = std::fs::read(&file_path).map_err(|e| e.to_string())?;
    use base64::Engine;
    Ok(base64::engine::general_purpose::STANDARD.encode(&data))
}

#[cfg(desktop)]
#[tauri::command]
fn resize_clock(app: tauri::AppHandle, width: f64, height: f64) {
    if let Some(cw) = app.get_webview_window(CLOCK_LABEL) {
        let _ = cw.set_size(tauri::Size::Physical(tauri::PhysicalSize {
            width: width as u32,
            height: height as u32,
        }));
    }
}

#[cfg(desktop)]
#[tauri::command]
fn show_context_menu(app: tauri::AppHandle, has_cd: bool, is_trans: bool) {
    match build_context_menu(&app, has_cd, is_trans) {
        Ok(menu) => {
            if let Some(cw) = app.get_webview_window(CLOCK_LABEL) {
                let _ = cw.popup_menu(&menu);
            }
        }
        Err(_) => {},
    }
}

#[cfg(desktop)]
fn close_clock(app: &tauri::AppHandle) {
    if let Some(cw) = app.get_webview_window(CLOCK_LABEL) {
        let _ = cw.hide();
    }
}

#[cfg(desktop)]
fn close_input(app: &tauri::AppHandle) {
    if let Some(iw) = app.get_webview_window(INPUT_LABEL) {
        let _ = iw.close();
    }
}

#[cfg(desktop)]
fn close_todo(app: &tauri::AppHandle) {
    if let Some(tw) = app.get_webview_window(TODO_LABEL) {
        let _ = tw.destroy();
    }
}

#[cfg(desktop)]
fn is_port_open(port: u16) -> bool {
    std::net::TcpStream::connect(format!("127.0.0.1:{}", port)).is_ok()
}

#[cfg(desktop)]
fn wait_for_backend(port: u16, timeout: Duration) -> bool {
    let addr = format!("127.0.0.1:{}", port);
    let start = Instant::now();
    while start.elapsed() < timeout {
        if std::net::TcpStream::connect(&addr).is_ok() { return true; }
        std::thread::sleep(Duration::from_millis(500));
    }
    false
}

#[cfg(desktop)]
fn try_embedded_sidecar(port: u16, app: &tauri::App) -> bool {
    let sidecar_bytes: &[u8] = include_bytes!(concat!(env!("OUT_DIR"), "/nexus-sidecar.exe"));
    if sidecar_bytes.len() < 1024 { return false; }
    let temp_dir = std::env::temp_dir().join("nexus-assistant");
    let _ = std::fs::create_dir_all(&temp_dir);
    let sidecar_path = temp_dir.join("nexus-server.exe");
    let need_extract = match std::fs::metadata(&sidecar_path) {
        Ok(meta) => meta.len() != sidecar_bytes.len() as u64,
        Err(_) => true,
    };
    if need_extract {
        if let Ok(mut f) = std::fs::File::create(&sidecar_path) { let _ = f.write_all(sidecar_bytes); }
    }
    let mut cmd = Command::new(&sidecar_path);
    cmd.args(["--port", &port.to_string()]);
    // 通过环境变量告知 sidecar 真正的 app 目录（用于数据存储和 open-webSearch 查找）
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            cmd.env("NEXUS_APP_DIR", dir);
        }
    }
    #[cfg(target_os = "windows")]
    cmd.creation_flags(CREATE_NO_WINDOW);
    match cmd.spawn() {
        Ok(child) => {
            let state = app.state::<BackendProcess>();
            *state.0.lock().unwrap() = Some(child);
            wait_for_backend(port, Duration::from_secs(30))
        }
        Err(_) => false
    }
}

/// 创建原生右键菜单
#[cfg(desktop)]
fn build_context_menu(app: &tauri::AppHandle, has_cd: bool, is_trans: bool) -> tauri::Result<Menu<tauri::Wry>> {
    let menu = Menu::new(app)?;
    let m15 = MenuItem::with_id(app, "cd15", "⏱ 15 分钟", true, None::<&str>)?;
    let m30 = MenuItem::with_id(app, "cd30", "⏱ 30 分钟", true, None::<&str>)?;
    let m45 = MenuItem::with_id(app, "cd45", "⏱ 45 分钟", true, None::<&str>)?;
    let m60 = MenuItem::with_id(app, "cd60", "⏱ 60 分钟", true, None::<&str>)?;
    let m90 = MenuItem::with_id(app, "cd90", "⏱ 90 分钟", true, None::<&str>)?;
    let sep1 = PredefinedMenuItem::separator(app)?;
    let mcustom = MenuItem::with_id(app, "custom", "✏️ 自定义...", true, None::<&str>)?;
    let sep2 = PredefinedMenuItem::separator(app)?;
    let mcancel = MenuItem::with_id(app, "cancel", "⏹ 取消倒计时", true, None::<&str>)?;
    let bg_text = if is_trans { "🎨 切换黑色背景" } else { "🎨 切换透明背景" };
    let mbg = MenuItem::with_id(app, "bg", bg_text, true, None::<&str>)?;
    let sep3 = PredefinedMenuItem::separator(app)?;
    let mgames = MenuItem::with_id(app, "games", "🎮 游戏机模式", true, None::<&str>)?;
    let mtodo = MenuItem::with_id(app, "todo", "📋 显示待办日历", true, None::<&str>)?;
    let sep4 = PredefinedMenuItem::separator(app)?;
    let mback = MenuItem::with_id(app, "back", "↩ 返回主窗口", true, None::<&str>)?;
    menu.append_items(&[&m15, &m30, &m45, &m60, &m90, &sep1, &mcustom, &sep2, &mcancel, &mbg, &sep3, &mgames, &mtodo, &sep4, &mback])?;
    Ok(menu)
}

/// 创建时钟窗口（异步，避免菜单事件死锁）
#[cfg(desktop)]
fn create_clock_window(app: &tauri::AppHandle) {
    let app_handle = app.clone();
    // 在新线程中执行，避免阻塞菜单事件处理
    std::thread::spawn(move || {
        do_create_clock(&app_handle);
    });
}

#[cfg(desktop)]
fn do_create_clock(app: &tauri::AppHandle) {
    // 尝试显示已有窗口（隐藏状态的窗口仍存在）
    if let Some(cw) = app.get_webview_window(CLOCK_LABEL) {
        let _ = cw.show();
        let _ = cw.set_focus();
        return;
    }

    let ipc_script = r#"
        (function() {
            function setup() {
                if (window.__TAURI_INTERNALS__ && !window.__nexus_ipc) {
                    window.__nexus_ipc = true;
                    window.invoke = window.__TAURI_INTERNALS__.invoke;
                    window.startDrag = function() {
                        window.__TAURI_INTERNALS__.invoke('plugin:window|start_dragging', {});
                    };
                    console.log('[nexus-clock] IPC ready');
                }
            }
            setup();
            if (!window.__nexus_ipc) {
                var t = setInterval(function(){setup();if(window.__nexus_ipc)clearInterval(t);},50);
                setTimeout(function(){clearInterval(t);},5000);
            }
        })();
    "#;

    let win = match tauri::WebviewWindowBuilder::new(
        app, CLOCK_LABEL, WebviewUrl::App("clock.html".into()),
    )
    .title("Nexus Clock")
    .inner_size(360.0, 180.0)
    .resizable(true)
    .decorations(false)
    .transparent(true)
    .always_on_top(true)
    .initialization_script(ipc_script)
    .center()
    .build()
    {
        Ok(w) => w,
        Err(_) => return,
    };

    // 注入全局函数供 HTML 调用
    let _ = win.eval(r#"
        window.startCountdown = function(m) {
            window._isCD = true; window._cdDone = false;
            window._cdTarget = Date.now() + m * 60000;
        };
        window.cancelCountdown = function() {
            window._isCD = false; window._cdDone = false;
        };
        window.toggleBg = function() {
            window._trans = !window._trans;
            document.body.classList.toggle('transparent', window._trans);
        };
        window.getState = function() {
            return JSON.stringify({cd: !!window._isCD, trans: !!window._trans});
        };
    "#);

    // 右键菜单事件处理已移至 setup 中的全局 on_menu_event，避免重复注册
}

/// 创建待办日历窗口（带创建锁，防止并发重复创建）
#[cfg(desktop)]
fn create_todo_window(app: &tauri::AppHandle) {
    // 自旋锁：确保同一时刻只有一个线程在创建窗口
    while TODO_CREATING.compare_exchange_weak(false, true, Ordering::SeqCst, Ordering::SeqCst).is_err() {
        std::thread::sleep(Duration::from_millis(5));
    }

    let app_handle = app.clone();
    // 检查是否已有窗口，有则聚焦
    if let Some(tw) = app_handle.get_webview_window(TODO_LABEL) {
        let _ = tw.set_focus();
        TODO_CREATING.store(false, Ordering::SeqCst);
        return;
    }

    do_create_todo(&app_handle);
    TODO_CREATING.store(false, Ordering::SeqCst);
}

#[cfg(desktop)]
fn do_create_todo(app: &tauri::AppHandle) {
    let ipc_script = r#"
        (function() {
            function setup() {
                if (window.__TAURI_INTERNALS__ && !window.__nexus_ipc) {
                    window.__nexus_ipc = true;
                    window.invoke = window.__TAURI_INTERNALS__.invoke;
                    console.log('[nexus-todo] IPC ready');
                }
            }
            setup();
            if (!window.__nexus_ipc) {
                var t = setInterval(function(){setup();if(window.__nexus_ipc)clearInterval(t);},50);
                setTimeout(function(){clearInterval(t);},5000);
            }
        })();
    "#;

    let _ = tauri::WebviewWindowBuilder::new(
        app, TODO_LABEL, WebviewUrl::App("todo-calendar.html".into()),
    )
    .title("Nexus Todo")
    .inner_size(480.0, 320.0)
    .resizable(true)
    .decorations(false)
    .transparent(true)
    .always_on_top(true)
    .initialization_script(ipc_script)
    .build();
}

/// 创建游戏窗口（复古像素游戏机）
#[cfg(desktop)]
fn create_games_window(app: &tauri::AppHandle) {
    let app_handle = app.clone();
    std::thread::spawn(move || {
        let label = "games";
        // 如果已有窗口，聚焦
        if let Some(gw) = app_handle.get_webview_window(label) {
            let _ = gw.show();
            let _ = gw.set_focus();
            return;
        }

        let ipc_script = r#"
            (function() {
                function setup() {
                    if (window.__TAURI_INTERNALS__ && !window.__nexus_ipc) {
                        window.__nexus_ipc = true;
                        window.invoke = window.__TAURI_INTERNALS__.invoke;
                        console.log('[nexus-games] IPC ready');
                    }
                }
                setup();
                if (!window.__nexus_ipc) {
                    var t = setInterval(function(){setup();if(window.__nexus_ipc)clearInterval(t);},50);
                    setTimeout(function(){clearInterval(t);},5000);
                }
            })();
        "#;

        let _ = tauri::WebviewWindowBuilder::new(
            &app_handle, label, WebviewUrl::App("games.html".into()),
        )
        .title("Retro Arcade")
        .inner_size(480.0, 640.0)
        .resizable(false)
        .decorations(true)
        .always_on_top(false)
        .initialization_script(ipc_script)
        .center()
        .build();
    });
}

/// 创建自定义倒计时输入窗口
#[cfg(desktop)]
fn create_input_window(app: &tauri::AppHandle) {
    if let Some(iw) = app.get_webview_window(INPUT_LABEL) {
        let _ = iw.show();
        let _ = iw.set_focus();
        return;
    }

    // 与时钟窗口相同的 IPC 注入
    let ipc_script = r#"
        (function() {
            function setup() {
                if (window.__TAURI_INTERNALS__ && !window.__nexus_ipc) {
                    window.__nexus_ipc = true;
                    window.invoke = window.__TAURI_INTERNALS__.invoke;
                }
            }
            setup();
            if (!window.__nexus_ipc) {
                var t = setInterval(function(){setup();if(window.__nexus_ipc)clearInterval(t);},50);
                setTimeout(function(){clearInterval(t);},5000);
            }
        })();
    "#;

    let html = r#"<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#1a1a2e;font-family:Consolas,monospace;display:flex;flex-direction:column;
  align-items:center;justify-content:center;height:100vh;-webkit-user-select:none}
label{color:#cc6600;font-size:12px;margin-bottom:6px;letter-spacing:1px}
.row{display:flex;gap:8px;align-items:center}
input{width:70px;background:#0e0e12;border:1px solid #333346;border-radius:6px;
  color:#ffe8aa;padding:8px;font-size:18px;text-align:center;outline:none;font-family:Consolas,monospace}
input:focus{border-color:#ff8c00;box-shadow:0 0 8px rgba(255,140,0,0.3)}
button{background:#ff8c00;border:none;border-radius:6px;color:#fff;padding:8px 18px;
  font-size:14px;cursor:pointer;font-family:Consolas,monospace}
button:hover{background:#ffaa33}
.hint{color:#64748b;font-size:10px;margin-top:8px}
</style></head><body>
<label>SET COUNTDOWN (MIN)</label>
<div class="row">
  <input type="number" id="min" min="1" max="999" value="45" autofocus>
  <button id="ok">START</button>
</div>
<div class="hint">Enter to confirm · Esc to cancel</div>
<script>
var invoke = (window.__TAURI_INTERNALS__||{}).invoke;
document.getElementById('ok').onclick=function(){
  var v=parseInt(document.getElementById('min').value);
  if(v>0&&invoke)invoke('set_countdown',{minutes:v});
};
document.getElementById('min').onkeydown=function(e){
  if(e.key==='Enter')document.getElementById('ok').click();
  if(e.key==='Escape'&&invoke)invoke('close_clock_window',{});
};
document.getElementById('min').select();
</script></body></html>"#;

    let _ = tauri::WebviewWindowBuilder::new(
        app, INPUT_LABEL, WebviewUrl::App("countdown-input.html".into()),
    )
    .title("Countdown")
    .inner_size(260.0, 120.0)
    .resizable(false)
    .decorations(false)
    .always_on_top(true)
    .initialization_script(ipc_script)
    .center()
    .build();
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let mut builder = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_os::init())
        .plugin(tauri_plugin_dialog::init());

    // 注册命令：桌面端包含所有命令，移动端只包含跨平台命令
    #[cfg(desktop)]
    {
        builder = builder.invoke_handler(tauri::generate_handler![
            greet, show_main_window, close_clock_window, close_input_window, close_todo_window,
            set_countdown, cancel_countdown, toggle_bg,
            show_context_menu, resize_clock,
            list_audio_files, read_file_base64
        ]);
    }
    #[cfg(mobile)]
    {
        builder = builder.invoke_handler(tauri::generate_handler![
            greet, list_audio_files, read_file_base64
        ]);
    }

    // 桌面端专用：updater 插件
    #[cfg(desktop)]
    {
        builder = builder.plugin(tauri_plugin_updater::Builder::new().build());
        builder = builder.plugin(tauri_plugin_process::init());
    }

    // 桌面端专用：后端进程管理
    #[cfg(desktop)]
    {
        builder = builder.manage(BackendProcess(Mutex::new(None)));
    }

    builder
        .setup(|app| {
            // 桌面端：系统托盘 + 多窗口
            #[cfg(desktop)]
            {
                let show_item = MenuItem::with_id(app, "show", "显示主窗口", true, None::<&str>)?;
                let clock_item = MenuItem::with_id(app, "clock", "显示时钟", true, None::<&str>)?;
                let todo_item = MenuItem::with_id(app, "todo", "显示待办日历", true, None::<&str>)?;
                let exit_item = MenuItem::with_id(app, "exit", "退出", true, None::<&str>)?;
                let menu = Menu::with_items(app, &[&show_item, &clock_item, &todo_item, &exit_item])?;

                let _tray = TrayIconBuilder::new()
                    .icon(app.default_window_icon().unwrap().clone())
                    .tooltip("AI Nexus Assistant")
                    .menu(&menu)
                    .on_tray_icon_event(|tray, event| {
                        if let TrayIconEvent::DoubleClick { button: MouseButton::Left, .. } = event {
                            show_main_window(tray.app_handle().clone());
                        }
                    })
                    .build(app)?;

                // 全局菜单事件处理
                app.on_menu_event(move |app, event| {
                    let id = event.id().as_ref();
                    match id {
                        "cd15" => { set_countdown(app.clone(), 15); }
                        "cd30" => { set_countdown(app.clone(), 30); }
                        "cd45" => { set_countdown(app.clone(), 45); }
                        "cd60" => { set_countdown(app.clone(), 60); }
                        "cd90" => { set_countdown(app.clone(), 90); }
                        "custom" => { create_input_window(app); }
                        "cancel" => { cancel_countdown(app.clone()); }
                        "bg" => { toggle_bg(app.clone()); }
                        "games" => { create_games_window(app); }
                        "todo" => { create_todo_window(app); }
                        "back" => { show_main_window(app.clone()); }
                        "show" => { show_main_window(app.clone()); }
                        "clock" => { create_clock_window(app); }
                        "exit" => {
                            #[cfg(desktop)]
                            {
                                if let Some(s) = app.try_state::<BackendProcess>() {
                                    if let Ok(mut g) = s.0.lock() {
                                        if let Some(ref mut c) = *g {
                                            kill_process_tree(c.id());
                                            let _ = c.wait();
                                        }
                                        *g = None;
                                    }
                                }
                            }
                            app.exit(0);
                        }
                        _ => {}
                    }
                });

                // 主窗口关闭 → 时钟
                let ah = app.handle().clone();
                if let Some(window) = app.get_webview_window("main") {
                    window.on_window_event(move |event| {
                        if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                            api.prevent_close();
                            if let Some(w) = ah.get_webview_window("main") {
                                let _ = w.eval("window.dispatchEvent(new CustomEvent('nexus-window-hide'))");
                                let _ = w.set_skip_taskbar(true);
                                let _ = w.hide();
                            }
                            create_clock_window(&ah);
                            create_todo_window(&ah);
                        }
                    });
                }

                // 启动后端 sidecar
                let port: u16 = 8765;
                if !is_port_open(port) {
                    let mut started = try_embedded_sidecar(port, app);
                    if let Ok(exe) = std::env::current_exe() {
                        if let Some(dir) = exe.parent() {
                            if !started {
                                let mut cmd = Command::new(dir.join("nexus-server-x86_64-pc-windows-msvc.exe"));
                                cmd.args(["--port",&port.to_string()]);
                                cmd.env("NEXUS_APP_DIR", dir);
                                #[cfg(target_os = "windows")]
                                cmd.creation_flags(CREATE_NO_WINDOW);
                                if let Ok(c) = cmd.spawn() {
                                    *app.state::<BackendProcess>().0.lock().unwrap() = Some(c);
                                    started = wait_for_backend(port, Duration::from_secs(30));
                                }
                            }
                            if !started {
                                let mut cmd = Command::new("python");
                                cmd.arg(dir.join("server.py")).args(["--port",&port.to_string()]);
                                #[cfg(target_os = "windows")]
                                cmd.creation_flags(CREATE_NO_WINDOW);
                                if let Ok(c) = cmd.spawn() {
                                    *app.state::<BackendProcess>().0.lock().unwrap() = Some(c);
                                    started = wait_for_backend(port, Duration::from_secs(15));
                                }
                            }
                        }
                    }
                }
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
