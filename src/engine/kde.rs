//! KDE build: no mpvpaper process ownership. Explicit selections use the private-backup bridge.
use crate::scanner::VideoItem;
use std::{
    io,
    path::{Path, PathBuf},
    process::Command,
};

fn bridge() -> PathBuf {
    std::env::var_os("AURA_KDE_BRIDGE")
        .map(PathBuf::from)
        .unwrap_or_else(|| {
            Path::new(env!("CARGO_MANIFEST_DIR")).join("../../tools/aura_kde_bridge.py")
        })
}
pub fn call(action: &str, argument: Option<&Path>) -> Result<String, String> {
    let mut command = Command::new("python3");
    command.arg(bridge()).arg(action);
    if let Some(arg) = argument {
        command.arg(arg);
    }
    let out = command.output().map_err(|e| e.to_string())?;
    let stdout = String::from_utf8_lossy(&out.stdout).into_owned();
    if !out.status.success() {
        return Err(format!(
            "{}\n{}",
            stdout,
            String::from_utf8_lossy(&out.stderr)
        ));
    }
    Ok(stdout)
}
pub fn catalog() -> Result<Vec<VideoItem>, String> {
    let raw = call("catalog", None)?;
    parse_catalog(&raw)
}

fn parse_catalog(raw: &str) -> Result<Vec<VideoItem>, String> {
    let entries: Vec<serde_json::Value> = serde_json::from_str(raw).map_err(|e| e.to_string())?;
    let mut items = Vec::new();
    for e in entries {
        let available = e["usable"] == true;
        let Some(path) = e["project"].as_str() else {
            continue;
        };
        // Filtrar fondos no disponibles del selector
        if !available {
            continue;
        }
        let kind = e["type"].as_str().unwrap_or("unknown");
        let title = e["title"].as_str().unwrap_or("Wallpaper");
        let name = if available {
            format!("{title} · {kind}")
        } else {
            format!("{title} · no disponible ({kind})")
        };
        items.push(VideoItem {
            available,
            path: PathBuf::from(path),
            name_lower: name.to_lowercase(),
            name,
            size_bytes: 0,
            size_formatted: kind.into(),
            modified: e["modified"].as_u64().unwrap_or(0),
            thumb_path: e["preview"].as_str().map(PathBuf::from).or_else(|| {
                let cached = crate::scanner::thumbs::thumb_path_for_video(Path::new(path));
                cached.is_file().then_some(cached)
            }),
            is_video: kind != "image",
            is_downloaded: e["downloaded"] == true,
        });
    }
    Ok(items)
}
fn unsupported() -> io::Error {
    io::Error::new(io::ErrorKind::Unsupported, "Use the KDE selection action")
}
pub struct WallpaperEngine;
impl WallpaperEngine {
    pub fn new() -> Self {
        Self
    }
    pub fn processes_keys(&self) -> Vec<String> {
        Vec::new()
    }
    pub fn reap_dead_processes(&mut self) -> Vec<String> {
        Vec::new()
    }
    pub fn set_wallpaper(
        &mut self,
        _: &str,
        _: &str,
        _: &str,
        _: bool,
        _: u8,
        _: &str,
        _: bool,
        _: &str,
    ) -> io::Result<u32> {
        Err(unsupported())
    }
    pub fn set_volume(&mut self, _: Option<&str>, _: u8) -> bool {
        false
    }
    pub fn set_mute(&mut self, _: Option<&str>, _: bool) -> bool {
        false
    }
    pub fn set_scaling(&mut self, _: &str, _: &str) -> bool {
        false
    }
    pub fn toggle_pause(&mut self) -> bool {
        false
    }
    pub fn pause_all(&mut self) {}
    pub fn resume_all(&mut self) {}
    pub fn stop_output(&mut self, _: &str) {}
    pub fn stop_all(&mut self) {}
    pub fn write_autostart() -> io::Result<()> {
        Err(unsupported())
    }
    pub fn remove_autostart() -> io::Result<()> {
        Err(unsupported())
    }
    pub fn is_autostart_enabled() -> bool {
        false
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn workshop_types_and_missing_resources() {
        let items = parse_catalog(r#"[
            {"usable":true,"project":"/Steam/123/project.json","type":"scene","title":"日本","preview":"/Steam/123/preview.jpg"},
            {"usable":true,"project":"/Steam/456/project.json","type":"web","title":"Clock"},
            {"usable":false,"project":"/Steam/789/project.json","type":"video","title":"Missing"}
        ]"#).unwrap();
        assert_eq!(items.len(), 2, "should filter unavailable wallpapers");
        assert_eq!(items[0].name, "日本 · scene");
        assert_eq!(
            items[0].thumb_path,
            Some(PathBuf::from("/Steam/123/preview.jpg"))
        );
        assert_eq!(items[1].size_formatted, "web");
    }
    #[test]
    fn invalid_bridge_response_is_reported() {
        assert!(parse_catalog("bad json").is_err());
    }
}
