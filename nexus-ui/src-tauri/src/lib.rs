use std::process::{Command, Child};
use std::sync::Mutex;
use std::time::{Duration, Instant};
use tauri::Manager;

struct BackendProcess(Mutex<Option<Child>>);

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! Welcome to AI Nexus Assistant.", name)
}

/// TCP 探测后端端口是否就绪
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
            let mut backend_started = false;
            let port: u16 = 8765;

            if let Ok(exe_path) = std::env::current_exe() {
                if let Some(exe_dir) = exe_path.parent() {
                    // 方式1: 查找 sidecar exe
                    let sidecar = exe_dir.join("nexus-server-x86_64-pc-windows-msvc.exe");
                    if sidecar.exists() {
                        println!("[Nexus] Found sidecar: {:?}", sidecar);
                        match Command::new(&sidecar)
                            .args(["--port", &port.to_string()])
                            .stdout(std::process::Stdio::null())
                            .stderr(std::process::Stdio::null())
                            .spawn()
                        {
                            Ok(child) => {
                                println!("[Nexus] Sidecar spawned (PID {}), waiting for port {port}...", child.id());
                                let state = app.state::<BackendProcess>();
                                *state.0.lock().unwrap() = Some(child);

                                if wait_for_backend(port, Duration::from_secs(30)) {
                                    println!("[Nexus] Backend ready on port {port}");
                                    backend_started = true;
                                } else {
                                    eprintln!("[Nexus] Backend timeout after 30s on port {port}");
                                }
                            }
                            Err(e) => eprintln!("[Nexus] Sidecar spawn failed: {e}"),
                        }
                    } else {
                        println!("[Nexus] Sidecar not found at {:?}", sidecar);
                    }

                    // 方式2: 查找 server.py (开发模式)
                    if !backend_started {
                        let server_py = exe_dir.join("server.py");
                        if server_py.exists() {
                            println!("[Nexus] Found server.py, starting via python...");
                            match Command::new("python")
                                .arg(&server_py)
                                .args(["--port", &port.to_string()])
                                .spawn()
                            {
                                Ok(child) => {
                                    println!("[Nexus] Python backend started (PID {})", child.id());
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
            } else {
                eprintln!("[Nexus] Cannot determine exe path");
            }

            if !backend_started {
                eprintln!("[Nexus] Backend not auto-started. Run manually: python server.py");
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
