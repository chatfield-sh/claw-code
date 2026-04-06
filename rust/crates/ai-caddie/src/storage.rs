use anyhow::{Context, Result};
use std::path::PathBuf;

use crate::round::Round;

fn data_dir() -> Result<PathBuf> {
    let base = std::env::var("HOME").map_or_else(|_| PathBuf::from("."), PathBuf::from);
    let dir = base.join(".ai-caddie").join("rounds");
    std::fs::create_dir_all(&dir).context("Failed to create data directory")?;
    Ok(dir)
}

fn round_path(id: &str) -> Result<PathBuf> {
    Ok(data_dir()?.join(format!("{id}.json")))
}

pub fn save_round(round: &Round) -> Result<()> {
    let path = round_path(&round.id)?;
    let json = serde_json::to_string_pretty(round).context("Failed to serialize round")?;
    std::fs::write(&path, json).with_context(|| format!("Failed to write {}", path.display()))
}

pub fn load_all_rounds() -> Result<Vec<Round>> {
    let dir = data_dir()?;
    let mut rounds = Vec::new();
    for entry in std::fs::read_dir(&dir).context("Failed to read data directory")? {
        let entry = entry?;
        if entry.path().extension().and_then(|e| e.to_str()) == Some("json") {
            match std::fs::read_to_string(entry.path())
                .ok()
                .and_then(|s| serde_json::from_str::<Round>(&s).ok())
            {
                Some(r) => rounds.push(r),
                None => eprintln!("Warning: could not parse {}", entry.path().display()),
            }
        }
    }
    // Sort by date, newest first
    rounds.sort_by(|a, b| b.date.cmp(&a.date));
    Ok(rounds)
}

pub fn load_active_round() -> Option<Round> {
    load_all_rounds().ok()?.into_iter().find(|r| !r.is_complete)
}
