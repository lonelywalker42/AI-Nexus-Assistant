use std::process::{Command, Child};
use std::sync::Mutex;
use std::time::{Duration, Instant};
use tauri::Manager;

struct BackendProcess(Mutex<Option<Child>>);

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! Welcome to AI Nexus Assistant.", name)
}

/// 检查端口是否已被占用（后端是否已在运行）
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

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(BackendProcess(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![greet])
        .setup(|app| {
            let port: u16 = 8765;

            // ① 先检查后端是否已在运行
            if is_port_open(port) {
                println!("[Nexus] Backend already running on port {port}");
                return Ok(());
            }

            let mut backend_started = false;

            if let Ok(exe_path) = std::env::current_exe() {
                if let Some(exe_dir) = exe_path.parent() {
                    // 方式1: 查找 sidecar exe
                    let sidecar = exe_dir.join("nexus-server-x86_64-pc-windows-msvc.exe");
                    if sidecar.exists() {
                        println!("[Nexus] Found sidecar: {:?}", sidecar);
                        match Command::new(&sidecar)
                            .args(["--port", &port.to_string()])
                            .spawn()
                        {
                            Ok(child) => {
                                println!("[Nexus] Sidecar spawned (PID {}), waiting...", child.id());
                                let state = app.state::<BackendProcess>();
                                *state.0.lock().unwrap() = Some(child);

                                if wait_for_backend(port, Duration::from_secs(30)) {
                                    println!("[Nexus] Backend ready on port {port}");
                                    backend_started = true;
                                } else {
                                    eprintln!("[Nexus] Backend timeout after 30s");
                                }
                            }
                            Err(e) => eprintln!("[Nexus] Sidecar spawn failed: {e}"),
                        }
                    } else {
                        println!("[Nexus] Sidecar not found: {:?}", sidecar);
                    }

                    // 方式2: 查找 server.py (开发模式)
                    if !backend_started {
                        let server_py = exe_dir.join("server.py");
                        if server_py.exists() {
                            println!("[Nexus] Trying python server.py...");
                            match Command::new("python")
                                .arg(&server_py)
                                .args(["--port", &port.to_string()])
                                .spawn()
                            {
                                Ok(child) => {
                                    let state = app.state::<BackendProcess>();
                                    *state.0.lock().unwrap() = Some(child);
                                    if wait_for_backend(port, Duration::from_secs(15)) {
                                        println!("[Nexus] Backend ready on port {port}");
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
