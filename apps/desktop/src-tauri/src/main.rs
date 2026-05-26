use std::path::PathBuf;
use std::process::Command;

use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ParsedPdf {
    file_name: String,
    file_hash: String,
    text: String,
    text_format: String,
    text_length: usize,
}

#[tauri::command]
fn parse_pdf_to_markdown(path: String) -> Result<ParsedPdf, String> {
    let pdf_path = PathBuf::from(path);
    if !pdf_path.is_file() {
        return Err(format!("PDF file not found: {}", pdf_path.display()));
    }

    let desktop_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .ok_or_else(|| "Unable to locate desktop parser project".to_string())?
        .to_path_buf();

    let output = Command::new("uv")
        .args(["run", "python", "-m", "desktop_parser.parse_pdf"])
        .arg(&pdf_path)
        .current_dir(desktop_dir)
        .output()
        .map_err(|error| format!("Failed to start local PDF parser: {error}"))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
        return Err(if stderr.is_empty() {
            "Local PDF parser failed".to_string()
        } else {
            stderr
        });
    }

    serde_json::from_slice(&output.stdout)
        .map_err(|error| format!("Local PDF parser returned invalid JSON: {error}"))
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![parse_pdf_to_markdown])
        .run(tauri::generate_context!())
        .expect("error while running Deep Dig desktop app");
}
