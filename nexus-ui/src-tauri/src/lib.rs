use std::process::{Command, Child};
use std::sync::Mutex;
use std::time::{Duration, Instant};
use std::io::Write;
use tauri::Manager;
use tauri::tray::{TrayIconBuilder, MouseButton, TrayIconEvent};
use tauri::menu::{Menu, MenuItem, PredefinedMenuItem};
use tauri::WebviewUrl;

struct BackendProcess(Mutex<Option<Child>>);

const CLOCK_LABEL: &str = "clock";
const INPUT_LABEL: &str = "countdown_input";

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! Welcome to AI Nexus Assistant.", name)
}

#[tauri::command]
fn show_main_window(app: tauri::AppHandle) {
    println!("[Nexus] show_main_window called");
    close_clock(&app);
    close_input(&app);
    if let Some(w) = app.get_webview_window("main") {
        let _ = w.set_skip_taskbar(false);
        let _ = w.show();
        let _ = w.set_focus();
    }
}

#[tauri::command]
fn close_clock_window(app: tauri::AppHandle) {
    println!("[Nexus] close_clock_window called");
    close_clock(&app);
}

#[tauri::command]
fn close_input_window(app: tauri::AppHandle) {
    close_input(&app);
}

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

#[tauri::command]
fn cancel_countdown(app: tauri::AppHandle) {
    if let Some(cw) = app.get_webview_window(CLOCK_LABEL) {
        let _ = cw.eval("(function() { window._isCD = false; window._cdDone = false; })();");
    }
}

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

#[tauri::command]
fn resize_clock(app: tauri::AppHandle, width: f64, height: f64) {
    if let Some(cw) = app.get_webview_window(CLOCK_LABEL) {
        let _ = cw.set_size(tauri::Size::Physical(tauri::PhysicalSize {
            width: width as u32,
            height: height as u32,
        }));
    }
}

#[tauri::command]
fn show_context_menu(app: tauri::AppHandle, has_cd: bool, is_trans: bool) {
    println!("[Nexus] show_context_menu called: has_cd={}, is_trans={}", has_cd, is_trans);
    match build_context_menu(&app, has_cd, is_trans) {
        Ok(menu) => {
            if let Some(cw) = app.get_webview_window(CLOCK_LABEL) {
                match cw.popup_menu(&menu) {
                    Ok(_) => println!("[Nexus] popup_menu OK"),
                    Err(e) => eprintln!("[Nexus] popup_menu failed: {e}"),
                }
            } else {
                eprintln!("[Nexus] clock window not found");
            }
        }
        Err(e) => eprintln!("[Nexus] build_context_menu failed: {e}"),
    }
}

fn close_clock(app: &tauri::AppHandle) {
    if let Some(cw) = app.get_webview_window(CLOCK_LABEL) {
        let _ = cw.close();
    }
}

fn close_input(app: &tauri::AppHandle) {
    if let Some(iw) = app.get_webview_window(INPUT_LABEL) {
        let _ = iw.close();
    }
}

fn is_port_open(port: u16) -> bool {
    std::net::TcpStream::connect(format!("127.0.0.1:{}", port)).is_ok()
}

fn wait_for_backend(port: u16, timeout: Duration) -> bool {
    let addr = format!("127.0.0.1:{}", port);
    let start = Instant::now();
    while start.elapsed() < timeout {
        if std::net::TcpStream::connect(&addr).is_ok() { return true; }
        std::thread::sleep(Duration::from_millis(500));
    }
    false
}

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
    match Command::new(&sidecar_path).args(["--port", &port.to_string()]).spawn() {
        Ok(child) => {
            let state = app.state::<BackendProcess>();
            *state.0.lock().unwrap() = Some(child);
            wait_for_backend(port, Duration::from_secs(30))
        }
        Err(_) => false
    }
}

/// 创建原生右键菜单
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
    let mback = MenuItem::with_id(app, "back", "↩ 返回主窗口", true, None::<&str>)?;
    menu.append_items(&[&m15, &m30, &m45, &m60, &m90, &sep1, &mcustom, &sep2, &mcancel, &mbg, &sep3, &mback])?;
    Ok(menu)
}

/// 创建时钟窗口（异步，避免菜单事件死锁）
fn create_clock_window(app: &tauri::AppHandle) {
    let app_handle = app.clone();
    // 在新线程中执行，避免阻塞菜单事件处理
    std::thread::spawn(move || {
        do_create_clock(&app_handle);
    });
}

fn do_create_clock(app: &tauri::AppHandle) {
    // 尝试聚焦已有窗口
    if let Some(cw) = app.get_webview_window(CLOCK_LABEL) {
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
    .inner_size(360.0, 140.0)
    .resizable(true)
    .decorations(false)
    .transparent(true)
    .always_on_top(true)
    .initialization_script(ipc_script)
    .center()
    .build()
    {
        Ok(w) => w,
        Err(e) => { eprintln!("[Nexus] Clock window failed: {e}"); return; }
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

    // 右键菜单由 JS contextmenu 事件触发 show_context_menu 命令

    // 注册菜单事件处理
    let app_handle = app.clone();
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
            "back" => { show_main_window(app.clone()); }
            _ => {}
        }
    });

    println!("[Nexus] Clock window created with native menu");
}

/// 创建自定义倒计时输入窗口
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
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(BackendProcess(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![
            greet, show_main_window, close_clock_window, close_input_window,
            set_countdown, cancel_countdown, toggle_bg,
            show_context_menu, resize_clock
        ])
        .setup(|app| {
            // 托盘
            let show_item = MenuItem::with_id(app, "show", "显示主窗口", true, None::<&str>)?;
            let clock_item = MenuItem::with_id(app, "clock", "显示时钟", true, None::<&str>)?;
            let exit_item = MenuItem::with_id(app, "exit", "退出", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show_item, &clock_item, &exit_item])?;

            let _tray = TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .tooltip("AI Nexus Assistant")
                .menu(&menu)
                .on_menu_event(move |app, event| {
                    match event.id().as_ref() {
                        "show" => { show_main_window(app.clone()); }
                        "clock" => { create_clock_window(app); }
                        "exit" => {
                            if let Some(s) = app.try_state::<BackendProcess>() {
                                if let Ok(mut g) = s.0.lock() {
                                    if let Some(ref mut c) = *g { let _ = c.kill(); }
                                }
                            }
                            app.exit(0);
                        }
                        _ => {}
                    }
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::DoubleClick { button: MouseButton::Left, .. } = event {
                        show_main_window(tray.app_handle().clone());
                    }
                })
                .build(app)?;

            // 主窗口关闭 → 时钟
            let ah = app.handle().clone();
            if let Some(window) = app.get_webview_window("main") {
                window.on_window_event(move |event| {
                    if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                        api.prevent_close();
                        if let Some(w) = ah.get_webview_window("main") {
                            let _ = w.set_skip_taskbar(true);
                            let _ = w.hide();
                        }
                        create_clock_window(&ah);
                    }
                });
            }

            // 启动后端
            let port: u16 = 8765;
            if is_port_open(port) { return Ok(()); }
            let mut started = try_embedded_sidecar(port, app);
            if let Ok(exe) = std::env::current_exe() {
                if let Some(dir) = exe.parent() {
                    if !started {
                        if let Ok(c) = Command::new(dir.join("nexus-server-x86_64-pc-windows-msvc.exe")).args(["--port",&port.to_string()]).spawn() {
                            *app.state::<BackendProcess>().0.lock().unwrap() = Some(c);
                            started = wait_for_backend(port, Duration::from_secs(30));
                        }
                    }
                    if !started {
                        if let Ok(c) = Command::new("python").arg(dir.join("server.py")).args(["--port",&port.to_string()]).spawn() {
                            *app.state::<BackendProcess>().0.lock().unwrap() = Some(c);
                            started = wait_for_backend(port, Duration::from_secs(15));
                        }
                    }
                }
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
