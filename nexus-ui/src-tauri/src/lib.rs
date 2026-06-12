use std::process::{Command, Child};
use std::sync::Mutex;
use tauri::Manager;

struct BackendProcess(Mutex<Option<Child>>);

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! Welcome to AI Nexus Assistant.", name)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(BackendProcess(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![greet])
        .setup(|app| {
            // 尝试启动 Python 后端
            // dev 模式: 用户手动运行 python server.py
            // release 模式: 查找同目录下的 sidecar exe

            let mut backend_started = false;

            // 方式1: 查找 exe 同目录下的 sidecar
            if let Ok(exe_path) = std::env::current_exe() {
                if let Some(exe_dir) = exe_path.parent() {
                    let sidecar = exe_dir.join("nexus-server-x86_64-pc-windows-msvc.exe");
                    if sidecar.exists() {
                        match Command::new(&sidecar).args(["--port", "8765"]).spawn() {
                            Ok(child) => {
                                println!("[Nexus] Sidecar started");
                                let state = app.state::<BackendProcess>();
                                *state.0.lock().unwrap() = Some(child);
                                backend_started = true;
                            }
                            Err(e) => eprintln!("[Nexus] Sidecar start failed: {e}"),
                        }
                    }

                    // 方式2: 查找 server.py (开发模式)
                    if !backend_started {
                        let server_py = exe_dir.join("server.py");
                        if server_py.exists() {
                            match Command::new("python").arg(&server_py).args(["--port", "8765"]).spawn() {
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
