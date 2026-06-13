fn main() {
    // 将 sidecar 复制到 OUT_DIR 供 include_bytes!() 使用
    let out_dir = std::env::var("OUT_DIR").unwrap();
    let sidecar_src = std::path::Path::new("binaries/nexus-server-x86_64-pc-windows-msvc.exe");
    let sidecar_dst = std::path::Path::new(&out_dir).join("nexus-sidecar.exe");

    if sidecar_src.exists() {
        std::fs::copy(sidecar_src, &sidecar_dst).expect("Failed to copy sidecar to OUT_DIR");
        println!("cargo:rerun-if-changed=binaries/nexus-server-x86_64-pc-windows-msvc.exe");
    } else {
        // 写入空占位符（嵌入模式禁用）
        std::fs::write(&sidecar_dst, b"").expect("Failed to write placeholder");
        println!("cargo:warning=Sidecar not found at binaries/, embedded mode disabled");
    }

    tauri_build::build();
}
