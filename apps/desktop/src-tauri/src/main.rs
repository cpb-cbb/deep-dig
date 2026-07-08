use std::fs;
use std::fs::File;
use std::io::{BufReader, Read};
use std::path::PathBuf;
use std::process::Command;

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

#[derive(Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct ParsedPdf {
    file_name: String,
    file_hash: String,
    text: String,
    text_format: String,
    text_length: usize,
    #[serde(default)]
    reused: bool,
    #[serde(default)]
    storage_path: Option<String>,
}

fn sha256_file(path: &PathBuf) -> Result<String, String> {
    let file = File::open(path).map_err(|error| format!("Failed to read PDF file: {error}"))?;
    let mut reader = BufReader::new(file);
    let mut hasher = Sha256::new();
    let mut buffer = [0_u8; 1024 * 64];

    loop {
        let read = reader
            .read(&mut buffer)
            .map_err(|error| format!("Failed to hash PDF file: {error}"))?;
        if read == 0 {
            break;
        }
        hasher.update(&buffer[..read]);
    }

    Ok(format!("sha256:{:x}", hasher.finalize()))
}

#[tauri::command]
fn parse_pdf_to_markdown(path: String, output_dir: String) -> Result<ParsedPdf, String> {
    let pdf_path = PathBuf::from(path);
    if !pdf_path.is_file() {
        return Err(format!("PDF file not found: {}", pdf_path.display()));
    }
    let file_hash = sha256_file(&pdf_path)?;
    let storage_key = file_hash.trim_start_matches("sha256:");
    let storage_dir = PathBuf::from(output_dir)
        .join("deep-dig-parsed")
        .join(&storage_key[..2]);
    fs::create_dir_all(&storage_dir).map_err(|error| format!("Failed to create parsed text folder: {error}"))?;
    let storage_path = storage_dir.join(format!("{storage_key}.json"));
    let storage_path_display = storage_path.display().to_string();

    if storage_path.is_file() {
        let mut parsed: ParsedPdf = serde_json::from_slice(
            &fs::read(&storage_path).map_err(|error| format!("Failed to read parsed text file: {error}"))?,
        )
        .map_err(|error| format!("Parsed text file is invalid: {error}"))?;
        parsed.reused = true;
        parsed.storage_path = Some(storage_path_display);
        return Ok(parsed);
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

    let mut parsed: ParsedPdf = serde_json::from_slice(&output.stdout)
        .map_err(|error| format!("Local PDF parser returned invalid JSON: {error}"))?;
    parsed.file_hash = file_hash;
    parsed.reused = false;
    parsed.storage_path = Some(storage_path_display);
    let parsed_json = serde_json::to_vec_pretty(&parsed)
        .map_err(|error| format!("Failed to serialize parsed text: {error}"))?;
    fs::write(&storage_path, parsed_json).map_err(|error| format!("Failed to save parsed text: {error}"))?;
    Ok(parsed)
}

#[tauri::command]
fn write_binary_file(path: String, bytes: Vec<u8>) -> Result<(), String> {
    std::fs::write(&path, bytes).map_err(|error| format!("Failed to save file: {error}"))
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![parse_pdf_to_markdown, write_binary_file])
        .run(tauri::generate_context!())
        .expect("error while running Deep Dig desktop app");
}
