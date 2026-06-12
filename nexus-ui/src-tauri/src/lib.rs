use tauri::Manager;
use tauri_plugin_shell::ShellExt;

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! Welcome to AI Nexus Assistant.", name)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![greet])
        .setup(|app| {
            // 启动 Python 后端 sidecar
            let shell = app.shell();
            let sidecar = shell
                .sidecar("nexus-server")
                .expect("Failed to create sidecar command")
                .args(["--port", "8765"]);

            let (_rx, _child) = sidecar.spawn().expect("Failed to spawn sidecar");

            // sidecar 进程会在 app 关闭时自动终止
            // _rx 可用于读取后端输出
            // _child 可用于手动终止

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
