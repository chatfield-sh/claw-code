use anyhow::{anyhow, Context, Result};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::fmt::Write as _;

use crate::round::{HoleScore, Round, Weather};
use crate::stats::RoundStats;

const API_URL: &str = "https://api.anthropic.com/v1/messages";
const MODEL: &str = "claude-sonnet-4-6";
const MAX_TOKENS: u32 = 512;

const CADDIE_SYSTEM_PROMPT: &str = "\
You are an expert AI golf caddie and coach with deep knowledge of course management, \
club selection, and swing technique. You speak like a seasoned tour caddie — direct, \
confident, and brief. Never pad your answers. When recommending a club, name it \
specifically (e.g. '7-iron', 'gap wedge', '3-wood'). Always factor in wind, lie, \
and the player's handicap when giving advice.";

#[derive(Serialize, Deserialize, Debug)]
struct Message {
    role: String,
    content: String,
}

#[derive(Serialize, Debug)]
struct ApiRequest<'a> {
    model: &'a str,
    max_tokens: u32,
    system: &'a str,
    messages: Vec<Message>,
}

#[derive(Deserialize, Debug)]
struct ContentBlock {
    text: String,
}

#[derive(Deserialize, Debug)]
struct ApiResponse {
    content: Vec<ContentBlock>,
}

fn api_key() -> Result<String> {
    std::env::var("ANTHROPIC_API_KEY").context(
        "ANTHROPIC_API_KEY environment variable not set.\nSet it with: export ANTHROPIC_API_KEY=sk-ant-...",
    )
}

async fn call_claude(client: &Client, prompt: &str, max_tokens: u32) -> Result<String> {
    let key = api_key()?;

    let body = ApiRequest {
        model: MODEL,
        max_tokens,
        system: CADDIE_SYSTEM_PROMPT,
        messages: vec![Message {
            role: "user".into(),
            content: prompt.to_owned(),
        }],
    };

    let resp = client
        .post(API_URL)
        .header("x-api-key", &key)
        .header("anthropic-version", "2023-06-01")
        .json(&body)
        .send()
        .await
        .context("Failed to reach Anthropic API")?;

    if !resp.status().is_success() {
        let http_status = resp.status();
        let text = resp.text().await.unwrap_or_default();
        return Err(anyhow!("API error {http_status}: {text}"));
    }

    let parsed: ApiResponse = resp.json().await.context("Failed to parse API response")?;

    parsed
        .content
        .into_iter()
        .next()
        .map(|b| b.text)
        .ok_or_else(|| anyhow!("Empty response from API"))
}

/// Parameters for a club recommendation request
pub struct ClubRequest<'a> {
    pub distance_to_pin: u16,
    pub distance_to_front: Option<u16>,
    pub wind_speed_mph: u8,
    pub wind_direction: &'a str,
    pub lie: &'a str,
    pub elevation_change_feet: i16,
    pub handicap_index: f64,
    pub hole_par: u8,
    pub hole_description: &'a str,
}

/// Club recommendation for a shot
pub async fn club_recommendation(client: &Client, req: &ClubRequest<'_>) -> Result<String> {
    let elevation_note = match req.elevation_change_feet.cmp(&0) {
        std::cmp::Ordering::Greater => format!("{} ft uphill", req.elevation_change_feet),
        std::cmp::Ordering::Less => {
            format!("{} ft downhill", req.elevation_change_feet.unsigned_abs())
        }
        std::cmp::Ordering::Equal => "flat".to_owned(),
    };

    let green_note = req
        .distance_to_front
        .map_or(String::new(), |d| format!("; front of green at {d} yards"));

    let prompt = format!(
        "Hole: par {}. {}.\n\
         Lie: {}. Distance to pin: {} yards{green_note}. \
         Elevation: {elevation_note}.\n\
         Wind: {} mph from {}.\n\
         Player handicap index: {:.1}.\n\n\
         Give a concise club recommendation (2–4 sentences max). \
         Name the exact club, the adjusted yardage you're playing, and one key swing thought.",
        req.hole_par,
        req.hole_description,
        req.lie,
        req.distance_to_pin,
        req.wind_speed_mph,
        req.wind_direction,
        req.handicap_index,
    );

    call_claude(client, &prompt, MAX_TOKENS).await
}

/// Short tip after completing a hole
pub async fn post_hole_tip(
    client: &Client,
    hole: &HoleScore,
    weather: Option<&Weather>,
) -> Result<String> {
    let score_desc = hole.score_name().map_or_else(
        || "score not recorded".into(),
        |n| format!("{n} ({})", score_display(hole.score_vs_par().unwrap_or(0))),
    );

    let putts_note = hole.putts.map_or(String::new(), |p| format!(", {p} putts"));

    let fairway_note = if hole.par > 3 {
        hole.fairway_hit.map_or("", |h| {
            if h {
                ", fairway hit"
            } else {
                ", missed fairway"
            }
        })
    } else {
        ""
    };

    let gir_note = hole
        .gir
        .map_or("", |g| if g { ", GIR" } else { ", missed GIR" });

    let weather_note = weather.map_or(String::new(), |w| format!("  Weather: {w}"));

    let prompt = format!(
        "Hole {}: par {}. Player made a {score_desc}{putts_note}{fairway_note}{gir_note}.{weather_note}\n\n\
         Give one concise coaching tip (2–3 sentences) to help the player improve on this type of hole.",
        hole.hole_number,
        hole.par,
    );

    call_claude(client, &prompt, MAX_TOKENS).await
}

/// Full post-round analysis
pub async fn analyze_round(
    client: &Client,
    round: &Round,
    round_stats: &RoundStats,
) -> Result<String> {
    let weather_note = round
        .weather
        .as_ref()
        .map_or(String::new(), |w| format!("Weather: {w}\n"));

    let hole_lines: String =
        round
            .holes
            .iter()
            .filter(|h| h.strokes.is_some())
            .fold(String::new(), |mut acc, h| {
                let score = h.score_name().unwrap_or("?");
                let vs_par = h.score_vs_par().map_or(String::new(), score_display);
                let putts = h.putts.map_or(String::new(), |p| format!(" {p}p"));
                let _ = writeln!(
                    acc,
                    "  H{:>2}: par {} → {} ({vs_par}){putts}",
                    h.hole_number, h.par, score
                );
                acc
            });

    let prompt = format!(
        "Round summary for {} (HCP {:.1}) at {}:\n\
         {weather_note}\
         Gross score: {} ({:+})\n\
         Front nine: {}  Back nine: {}\n\
         GIR: {}/{} ({:.0}%)  Fairways: {}/{} ({:.0}%)  Avg putts: {:.1}\n\
         Handicap differential: {:.1}\n\
         Hole-by-hole:\n{hole_lines}\n\
         Provide a thorough but concise post-round analysis (6–10 sentences). \
         Identify 2–3 strengths and 2–3 areas to improve with specific drills or strategies.",
        round.player_name,
        round.handicap_index,
        round.course_name,
        round.total_strokes(),
        round.score_vs_par(),
        round.front_nine_score(),
        round.back_nine_score(),
        round_stats.gir,
        round_stats.gir_opportunities,
        round_stats.gir_pct(),
        round_stats.fairways_hit,
        round_stats.fairway_opportunities,
        round_stats.fir_pct(),
        round_stats.avg_putts(),
        round.handicap_differential(),
    );

    call_claude(client, &prompt, 1024).await
}

/// Free-form question to the AI caddie
pub async fn ask(client: &Client, question: &str) -> Result<String> {
    call_claude(client, question, MAX_TOKENS).await
}

fn score_display(vs_par: i8) -> String {
    match vs_par.cmp(&0) {
        std::cmp::Ordering::Less => format!("{vs_par}"),
        std::cmp::Ordering::Equal => "E".into(),
        std::cmp::Ordering::Greater => format!("+{vs_par}"),
    }
}
