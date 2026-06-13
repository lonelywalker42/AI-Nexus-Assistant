use std::process::{Command, Child};
use std::sync::Mutex;
use std::time::{Duration, Instant};
use std::io::Write;
use tauri::Manager;
use tauri::tray::{TrayIconBuilder, MouseButton, TrayIconEvent};
use tauri::menu::{Menu, MenuItem};
use tauri::WebviewUrl;

struct BackendProcess(Mutex<Option<Child>>);

const CLOCK_LABEL: &str = "clock";

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! Welcome to AI Nexus Assistant.", name)
}

#[tauri::command]
fn show_main_window(app: tauri::AppHandle) {
    // 关闭时钟窗口
    if let Some(cw) = app.get_webview_window(CLOCK_LABEL) {
        let _ = cw.close();
    }
    // 显示主窗口并恢复任务栏
    if let Some(w) = app.get_webview_window("main") {
        let _ = w.set_skip_taskbar(false);
        let _ = w.show();
        let _ = w.set_focus();
    }
}

#[tauri::command]
fn close_clock_window(app: tauri::AppHandle) {
    if let Some(cw) = app.get_webview_window(CLOCK_LABEL) {
        let _ = cw.close();
    }
}

/// 检查端口是否已被占用
fn is_port_open(port: u16) -> bool {
    std::net::TcpStream::connect(format!("127.0.0.1:{}", port)).is_ok()
}

/// 轮询等待后端端口就绪
fn wait_for_backend(port: u16, timeout: Duration) -> bool {
    let addr = format!("127.0.0.1:{}", port);
    let start = Instant::now();
    while start.elapsed() < timeout {
        if std::net::TcpStream::connect(&addr).is_ok() {
            return true;
        }
        std::thread::sleep(Duration::from_millis(500));
    }
    false
}

/// 从嵌入的字节中提取 sidecar 并启动
fn try_embedded_sidecar(port: u16, app: &tauri::App) -> bool {
    let sidecar_bytes: &[u8] = include_bytes!(concat!(env!("OUT_DIR"), "/nexus-sidecar.exe"));
    if sidecar_bytes.len() < 1024 {
        return false;
    }

    let temp_dir = std::env::temp_dir().join("nexus-assistant");
    let _ = std::fs::create_dir_all(&temp_dir);
    let sidecar_path = temp_dir.join("nexus-server.exe");

    let need_extract = match std::fs::metadata(&sidecar_path) {
        Ok(meta) => meta.len() != sidecar_bytes.len() as u64,
        Err(_) => true,
    };

    if need_extract {
        println!("[Nexus] Extracting embedded sidecar to {:?}", sidecar_path);
        let mut file = match std::fs::File::create(&sidecar_path) {
            Ok(f) => f,
            Err(e) => { eprintln!("[Nexus] Failed to create sidecar file: {e}"); return false; }
        };
        if let Err(e) = file.write_all(sidecar_bytes) {
            eprintln!("[Nexus] Failed to write sidecar: {e}");
            return false;
        }
    }

    println!("[Nexus] Launching embedded sidecar...");
    match Command::new(&sidecar_path).args(["--port", &port.to_string()]).spawn() {
        Ok(child) => {
            println!("[Nexus] Embedded sidecar spawned (PID {})", child.id());
            let state = app.state::<BackendProcess>();
            *state.0.lock().unwrap() = Some(child);
            wait_for_backend(port, Duration::from_secs(30))
        }
        Err(e) => { eprintln!("[Nexus] Embedded sidecar spawn failed: {e}"); false }
    }
}

/// 创建时钟悬浮窗口
fn create_clock_window(app: &tauri::AppHandle) {
    // 如果已存在则显示
    if let Some(cw) = app.get_webview_window(CLOCK_LABEL) {
        let _ = cw.show();
        let _ = cw.set_focus();
        return;
    }

    let _ = tauri::WebviewWindowBuilder::new(
        app,
        CLOCK_LABEL,
        WebviewUrl::App("clock.html".into()),
    )
    .title("Nexus Clock")
    .inner_size(360.0, 130.0)
    .resizable(false)
    .decorations(false)
    .content_protected(false)
    .always_on_top(true)
    .center()
    .build();
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(BackendProcess(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![greet, show_main_window, close_clock_window])
        .setup(|app| {
            // ── 托盘右键菜单 ──
            let show_item = MenuItem::with_id(app, "show", "显示主窗口", true, None::<&str>)?;
            let clock_item = MenuItem::with_id(app, "clock", "显示时钟", true, None::<&str>)?;
            let exit_item = MenuItem::with_id(app, "exit", "退出", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show_item, &clock_item, &exit_item])?;

            // ── 系统托盘 ──
            let app_handle = app.handle().clone();
            let _tray = TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .tooltip("AI Nexus Assistant")
                .menu(&menu)
                .on_menu_event(move |app, event| {
                    match event.id().as_ref() {
                        "show" => {
                            if let Some(cw) = app.get_webview_window(CLOCK_LABEL) {
                                let _ = cw.close();
                            }
                            if let Some(w) = app.get_webview_window("main") {
                                let _ = w.set_skip_taskbar(false);
                                let _ = w.show();
                                let _ = w.set_focus();
                            }
                        }
                        "clock" => {
                            create_clock_window(app);
                        }
                        "exit" => {
                            if let Some(state) = app.try_state::<BackendProcess>() {
                                if let Ok(mut guard) = state.0.lock() {
                                    if let Some(ref mut child) = *guard {
                                        let _ = child.kill();
                                    }
                                }
                            }
                            app.exit(0);
                        }
                        _ => {}
                    }
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::DoubleClick { button: MouseButton::Left, .. } = event {
                        let app = tray.app_handle();
                        if let Some(cw) = app.get_webview_window(CLOCK_LABEL) {
                            let _ = cw.close();
                        }
                        if let Some(w) = app.get_webview_window("main") {
                            let _ = w.set_skip_taskbar(false);
                            let _ = w.show();
                            let _ = w.set_focus();
                        }
                    }
                })
                .build(app)?;

            // ── 主窗口关闭 → 隐藏到托盘 + 弹出时钟 ──
            let ah = app_handle.clone();
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

            // ── 启动后端 ──
            let port: u16 = 8765;
            if is_port_open(port) {
                println!("[Nexus] Backend already running on port {port}");
                return Ok(());
            }

            let mut backend_started = false;
            backend_started = try_embedded_sidecar(port, app);

            if let Ok(exe_path) = std::env::current_exe() {
                if let Some(exe_dir) = exe_path.parent() {
                    if !backend_started {
                        let sidecar = exe_dir.join("nexus-server-x86_64-pc-windows-msvc.exe");
                        if sidecar.exists() {
                            match Command::new(&sidecar).args(["--port", &port.to_string()]).spawn() {
                                Ok(child) => {
                                    let state = app.state::<BackendProcess>();
                                    *state.0.lock().unwrap() = Some(child);
                                    if wait_for_backend(port, Duration::from_secs(30)) {
                                        backend_started = true;
                                    }
                                }
                                Err(e) => eprintln!("[Nexus] Sidecar spawn failed: {e}"),
                            }
                        }
                    }

                    if !backend_started {
                        let server_py = exe_dir.join("server.py");
                        if server_py.exists() {
                            match Command::new("python").arg(&server_py).args(["--port", &port.to_string()]).spawn() {
                                Ok(child) => {
                                    let state = app.state::<BackendProcess>();
                                    *state.0.lock().unwrap() = Some(child);
                                    if wait_for_backend(port, Duration::from_secs(15)) {
                                        backend_started = true;
                                    }
                                }
                                Err(e) => eprintln!("[Nexus] Python start failed: {e}"),
                            }
                        }
                    }
                }
            }

            if !backend_started {
                eprintln!("[Nexus] Backend not started. Run manually: python server.py");
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
