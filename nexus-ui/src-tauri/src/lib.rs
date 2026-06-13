use std::process::{Command, Child};
use std::sync::Mutex;
use std::time::{Duration, Instant};
use tauri::Manager;

struct BackendProcess(Mutex<Option<Child>>);

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! Welcome to AI Nexus Assistant.", name)
}

/// 轮询后端直到 /api/dashboard 响应 200
fn wait_for_backend(port: u16, timeout: Duration) -> bool {
    let url = format!("http://127.0.0.1:{}/api/dashboard", port);
    let start = Instant::now();
    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
        .unwrap_or_default();

    while start.elapsed() < timeout {
        if let Ok(resp) = client.get(&url).send() {
            if resp.status().is_success() {
                return true;
            }
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

            // 方式1: 查找 exe 同目录下的 sidecar
            if let Ok(exe_path) = std::env::current_exe() {
                if let Some(exe_dir) = exe_path.parent() {
                    let sidecar = exe_dir.join("nexus-server-x86_64-pc-windows-msvc.exe");
                    if sidecar.exists() {
                        match Command::new(&sidecar).args(["--port", &port.to_string()]).spawn() {
                            Ok(child) => {
                                println!("[Nexus] Sidecar spawned, waiting for backend...");
                                let state = app.state::<BackendProcess>();
                                *state.0.lock().unwrap() = Some(child);

                                // 等待后端就绪（最多 30 秒）
                                if wait_for_backend(port, Duration::from_secs(30)) {
                                    println!("[Nexus] Backend ready on port {port}");
                                    backend_started = true;
                                } else {
                                    eprintln!("[Nexus] Backend timeout after 30s");
                                }
                            }
                            Err(e) => eprintln!("[Nexus] Sidecar start failed: {e}"),
                        }
                    }

                    // 方式2: 查找 server.py (开发模式)
                    if !backend_started {
                        let server_py = exe_dir.join("server.py");
                        if server_py.exists() {
                            match Command::new("python").arg(&server_py).args(["--port", &port.to_string()]).spawn() {
                                Ok(child) => {
                                    println!("[Nexus] Backend started via python server.py");
                                    let state = app.state::<BackendProcess>();
                                    *state.0.lock().unwrap() = Some(child);
                                    backend_started = true;
                                }
                                Err(e) => eprintln!("[Nexus] Backend start failed: {e}"),
                            }
                        }
                    }
                }
            }

            if !backend_started {
                eprintln!("[Nexus] Backend not auto-started. Run manually: python server.py");
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
