/// AI Caddie — an AI-powered golf scoring and coaching app.
///
/// Usage:
///   ai-caddie new           Start a new round (interactive setup)
///   ai-caddie play          Resume or start an in-progress round
///   ai-caddie scorecard     Print the current/last round scorecard
///   ai-caddie finish        Finalize round and get AI analysis
///   ai-caddie stats         Show career statistics
///   ai-caddie history       List all past rounds
///   ai-caddie ask <text>    Ask the AI caddie a free-form question
///   ai-caddie courses       List available course presets
///   ai-caddie help          Show this help
mod ai;
mod course;
mod display;
mod round;
mod stats;
mod storage;

use anyhow::{bail, Context, Result};
use reqwest::Client;
use rustyline::{error::ReadlineError, DefaultEditor};
use uuid::Uuid;

use crate::ai::ClubRequest;
use crate::course::{Course, ALL_COURSES};
use crate::round::{HoleScore, Round, Weather};
use crate::stats::{CareerStats, RoundStats};

// ─── Entry point ─────────────────────────────────────────────────────────────

#[tokio::main]
async fn main() {
    let args: Vec<String> = std::env::args().collect();
    let cmd = args.get(1).map_or("help", String::as_str);

    let result = match cmd {
        "new" => cmd_new(),
        "play" => cmd_play().await,
        "scorecard" | "card" => cmd_scorecard(),
        "finish" => cmd_finish().await,
        "stats" => cmd_stats(),
        "history" | "rounds" => cmd_history(),
        "ask" => cmd_ask(&args[2..]).await,
        "courses" => {
            cmd_courses();
            Ok(())
        }
        "help" | "--help" | "-h" => {
            print_help();
            Ok(())
        }
        other => {
            display::print_error(&format!("Unknown command '{other}'. Run 'ai-caddie help'."));
            std::process::exit(1);
        }
    };

    if let Err(e) = result {
        display::print_error(&format!("{e:#}"));
        std::process::exit(1);
    }
}

fn print_help() {
    println!();
    println!("  ⛳  AI Caddie  — AI-powered golf scoring & coaching");
    println!();
    println!("  COMMANDS");
    println!("    new           Start a new round (interactive setup)");
    println!("    play          Play/resume an in-progress round hole by hole");
    println!("    scorecard     Display current round scorecard");
    println!("    finish        Complete a round and get AI post-round analysis");
    println!("    stats         Career statistics and handicap index");
    println!("    history       List all saved rounds");
    println!("    ask <text>    Ask the AI caddie anything about your game");
    println!("    courses       List built-in course presets");
    println!("    help          Show this help");
    println!();
    println!("  ENVIRONMENT");
    println!("    ANTHROPIC_API_KEY   Required for AI features");
    println!();
    println!("  EXAMPLES");
    println!("    ai-caddie new");
    println!("    ai-caddie play");
    println!("    ai-caddie ask \"How do I stop slicing my driver?\"");
    println!("    ai-caddie finish");
    println!();
}

// ─── new ─────────────────────────────────────────────────────────────────────

fn cmd_new() -> Result<()> {
    println!();
    println!("  ⛳  New Round Setup");
    display::separator();

    let mut rl = DefaultEditor::new().context("Failed to init input")?;

    let player_name = prompt(&mut rl, "  Player name: ")?;
    let handicap_str = prompt(&mut rl, "  Handicap index (e.g. 12.4): ")?;
    let handicap_index: f64 = handicap_str
        .trim()
        .parse()
        .context("Invalid handicap index")?;

    // Course selection
    println!();
    println!("  Available courses:");
    for (i, c) in ALL_COURSES.iter().enumerate() {
        println!("    [{}] {} — {}", i + 1, c.name, c.location);
    }
    println!("    [0] Enter a custom course name");
    println!();

    let course_choice = prompt(&mut rl, "  Select course (number): ")?;
    let course_idx: usize = course_choice.trim().parse().unwrap_or(0);

    let (course_name, holes_template, tee_name, course_rating, slope_rating) =
        if course_idx >= 1 && course_idx <= ALL_COURSES.len() {
            let c = ALL_COURSES[course_idx - 1];
            let tee = prompt_tee(&mut rl, c)?;
            let rating = c.rating_for_tee(&tee);
            let slope = c.slope_for_tee(&tee);
            let holes = build_hole_templates(c, &tee);
            (c.name.to_owned(), holes, tee, rating, slope)
        } else {
            let name = prompt(&mut rl, "  Course name: ")?;
            let rating_str = prompt(&mut rl, "  Course rating (e.g. 71.2): ")?;
            let slope_str = prompt(&mut rl, "  Slope rating (e.g. 128): ")?;
            let rating: f64 = rating_str.trim().parse().context("Invalid course rating")?;
            let slope: u16 = slope_str.trim().parse().context("Invalid slope rating")?;
            let holes = build_generic_holes();
            (name, holes, "White".to_owned(), rating, slope)
        };

    // Weather (optional)
    let want_weather = prompt(&mut rl, "  Enter weather conditions? (y/N): ")?;
    let weather = if want_weather.trim().to_lowercase() == "y" {
        Some(prompt_weather(&mut rl)?)
    } else {
        None
    };

    let round = Round {
        id: Uuid::new_v4().to_string(),
        course_name,
        date: chrono::Local::now(),
        player_name: player_name.trim().to_owned(),
        handicap_index,
        tee_color: tee_name,
        course_rating,
        slope_rating,
        holes: holes_template,
        weather,
        ai_analysis: None,
        is_complete: false,
    };

    storage::save_round(&round)?;
    display::print_success(&format!(
        "Round created! Course HCP: {}  (rating {:.1} / slope {})",
        round.course_handicap(),
        round.course_rating,
        round.slope_rating
    ));
    println!("  Run 'ai-caddie play' to start scoring.");
    Ok(())
}

fn prompt_tee(rl: &mut DefaultEditor, course: &Course) -> Result<String> {
    println!();
    println!("  Tee options for {}:", course.name);
    println!(
        "    [1] Black / Tips  — {:.1} / {}  ({} yds)",
        course.rating_black,
        course.slope_black,
        course.total_yardage("black")
    );
    println!(
        "    [2] Blue / Back   — {:.1} / {}  ({} yds)",
        course.rating_blue,
        course.slope_blue,
        course.total_yardage("blue")
    );
    println!(
        "    [3] White / Men   — {:.1} / {}  ({} yds)",
        course.rating_white,
        course.slope_white,
        course.total_yardage("white")
    );
    println!(
        "    [4] Red / Forward — {:.1} / {}  ({} yds)",
        course.rating_red,
        course.slope_red,
        course.total_yardage("red")
    );

    let choice = prompt(rl, "  Select tee (1-4, default 3): ")?;
    let tee = match choice.trim() {
        "1" => "black",
        "2" => "blue",
        "4" => "red",
        _ => "white",
    };
    Ok(tee.to_owned())
}

fn prompt_weather(rl: &mut DefaultEditor) -> Result<Weather> {
    let temp = prompt(rl, "  Temperature (°F): ")?;
    let wind_speed = prompt(rl, "  Wind speed (mph): ")?;
    let wind_dir = prompt(rl, "  Wind direction (N/S/E/W/NE/etc.): ")?;
    let conditions = prompt(rl, "  Conditions (sunny/cloudy/rainy/windy): ")?;
    Ok(Weather {
        temperature_f: temp.trim().parse().unwrap_or(72),
        wind_speed_mph: wind_speed.trim().parse().unwrap_or(0),
        wind_direction: wind_dir.trim().to_uppercase(),
        conditions: conditions.trim().to_owned(),
    })
}

fn build_hole_templates(course: &Course, tee: &str) -> Vec<HoleScore> {
    course
        .holes
        .iter()
        .map(|h| HoleScore {
            hole_number: h.number,
            par: h.par,
            yardage: Course::yardage_for_tee(h, tee),
            stroke_index: h.stroke_index,
            strokes: None,
            putts: None,
            fairway_hit: None,
            gir: None,
            shots: Vec::new(),
            ai_tip: None,
        })
        .collect()
}

fn build_generic_holes() -> Vec<HoleScore> {
    let pars = [4u8, 5, 4, 3, 4, 5, 3, 4, 4, 4, 3, 5, 4, 4, 5, 3, 4, 4];
    let yds = [
        380u16, 510, 360, 165, 420, 540, 180, 415, 395, 440, 175, 520, 400, 425, 530, 140, 385, 430,
    ];
    pars.iter()
        .zip(yds.iter())
        .enumerate()
        .map(|(i, (&par, &yardage))| {
            // stroke index: spread evenly over 1-18 in order
            let stroke_index = u8::try_from((i * 2 + 1).min(17)).unwrap_or(17) + 1;
            HoleScore {
                hole_number: u8::try_from(i + 1).unwrap_or(18),
                par,
                yardage,
                stroke_index,
                strokes: None,
                putts: None,
                fairway_hit: None,
                gir: None,
                shots: Vec::new(),
                ai_tip: None,
            }
        })
        .collect()
}

// ─── play ─────────────────────────────────────────────────────────────────────

async fn cmd_play() -> Result<()> {
    let mut round = storage::load_active_round()
        .ok_or_else(|| anyhow::anyhow!("No active round. Run 'ai-caddie new' first."))?;

    let http = Client::new();
    let mut rl = DefaultEditor::new().context("Failed to init input")?;

    println!();
    println!("  ⛳  {} — {}", round.course_name, round.player_name);
    println!(
        "  Course HCP: {}  |  HCP index: {:.1}",
        round.course_handicap(),
        round.handicap_index
    );
    if let Some(w) = &round.weather {
        println!("  Weather: {w}");
    }

    for hole_idx in 0..round.holes.len() {
        if round.holes[hole_idx].strokes.is_some() {
            continue;
        }

        play_hole(&http, &mut rl, &mut round, hole_idx).await?;
    }

    println!();
    println!("  ── Round complete! ──────────────────────────────────");
    display::print_scorecard(&round);
    let round_stats = RoundStats::from_round(&round);
    display::print_round_stats(&round, &round_stats);

    let finish = prompt(&mut rl, "  Finalize round and get AI analysis? (Y/n): ")?;
    if finish.trim().to_lowercase() != "n" {
        finish_round_with(&http, &mut round, &round_stats).await?;
    }

    Ok(())
}

async fn play_hole(
    http: &Client,
    rl: &mut DefaultEditor,
    round: &mut Round,
    hole_idx: usize,
) -> Result<()> {
    let hole_ref = &round.holes[hole_idx];
    display::print_hole_header(hole_ref);

    // Show hole description if we know the course
    let desc = ALL_COURSES
        .iter()
        .find(|c| c.name == round.course_name)
        .and_then(|c| c.holes.iter().find(|h| h.number == hole_ref.hole_number))
        .map_or("", |h| h.description);
    if !desc.is_empty() {
        println!("  {desc}");
    }

    let ch = u8::try_from(round.course_handicap().max(0)).unwrap_or(0);
    let strokes_received = round.holes[hole_idx].strokes_received(ch);
    if strokes_received > 0 {
        println!("  Handicap strokes here: {strokes_received}");
    }

    // Caddie advice
    let want_advice = prompt(rl, "  [C]addie advice or [Enter] to skip: ")?;
    if want_advice.trim().to_lowercase().starts_with('c') {
        offer_caddie_advice(http, rl, round, hole_idx).await;
    }

    // Score entry
    let strokes = prompt_strokes(rl)?;
    let putts = prompt_putts(rl, strokes)?;
    let fairway_hit = prompt_fairway(rl, round.holes[hole_idx].par)?;
    let gir = prompt_gir(rl, strokes, round.holes[hole_idx].par)?;

    round.holes[hole_idx].strokes = Some(strokes);
    round.holes[hole_idx].putts = Some(putts);
    round.holes[hole_idx].fairway_hit = fairway_hit;
    round.holes[hole_idx].gir = gir;

    let hole = &round.holes[hole_idx];
    if let Some(name) = hole.score_name() {
        println!("  → {} {}", name, display::colored_score_cell(hole));
    }
    display::print_running_score(round);
    storage::save_round(round)?;

    // AI tip on bad holes or every 6 holes
    let vs_par = round.holes[hole_idx].score_vs_par().unwrap_or(0);
    if vs_par >= 2 || (hole_idx + 1).is_multiple_of(6) {
        let want_tip = prompt(rl, "  [T]ip from AI caddie? [Enter] to skip: ")?;
        if want_tip.trim().to_lowercase().starts_with('t') {
            println!("  Analyzing...");
            let hole = round.holes[hole_idx].clone();
            match ai::post_hole_tip(http, &hole, round.weather.as_ref()).await {
                Ok(tip) => {
                    round.holes[hole_idx].ai_tip = Some(tip.clone());
                    storage::save_round(round)?;
                    display::print_ai_response("Caddie Tip", &tip);
                }
                Err(e) => display::print_error(&format!("AI unavailable: {e}")),
            }
        }
    }

    // Half-way summary after hole 9
    if hole_idx + 1 == 9 {
        print_turn_summary(round);
    }

    Ok(())
}

fn print_turn_summary(round: &Round) {
    println!();
    println!("  ── Turn ── Front nine complete ─────────────────────");
    let front_par: i32 = round
        .holes
        .iter()
        .filter(|h| h.hole_number <= 9)
        .map(|h| i32::from(h.par))
        .sum();
    let rs = RoundStats::from_round(round);
    println!(
        "  Front 9: {}  ({:+})  GIR: {}/9  FIR: {}/{}",
        round.front_nine_score(),
        i32::try_from(round.front_nine_score()).unwrap_or(0) - front_par,
        rs.gir,
        rs.fairways_hit,
        rs.fairway_opportunities
    );
    println!();
}

async fn offer_caddie_advice(
    http: &Client,
    rl: &mut DefaultEditor,
    round: &Round,
    hole_idx: usize,
) {
    let dist_str = prompt_or_default(rl, "    Distance to pin (yards): ", "150");
    let dist: u16 = dist_str.trim().parse().unwrap_or(150);

    let dist_front_str = prompt_or_default(rl, "    Distance to front (leave blank if same): ", "");
    let dist_front = dist_front_str.trim().parse::<u16>().ok();

    let lie = prompt_or_default(rl, "    Lie (fairway/rough/bunker/tee): ", "fairway");
    let elev_str = prompt_or_default(rl, "    Elevation change feet (+up/-down, 0=flat): ", "0");
    let elev: i16 = elev_str.trim().parse().unwrap_or(0);

    let (wind_speed, wind_dir) = round.weather.as_ref().map_or((0u8, "N".to_owned()), |w| {
        (w.wind_speed_mph, w.wind_direction.clone())
    });

    let hole_desc = ALL_COURSES
        .iter()
        .find(|c| c.name == round.course_name)
        .and_then(|c| {
            c.holes
                .iter()
                .find(|h| h.number == round.holes[hole_idx].hole_number)
        })
        .map_or("", |h| h.description);

    let req = ClubRequest {
        distance_to_pin: dist,
        distance_to_front: dist_front,
        wind_speed_mph: wind_speed,
        wind_direction: &wind_dir,
        lie: lie.trim(),
        elevation_change_feet: elev,
        handicap_index: round.handicap_index,
        hole_par: round.holes[hole_idx].par,
        hole_description: hole_desc,
    };

    println!("  Thinking...");
    match ai::club_recommendation(http, &req).await {
        Ok(advice) => display::print_ai_response("AI Caddie", &advice),
        Err(e) => display::print_error(&format!("AI unavailable: {e}")),
    }
}

fn prompt_strokes(rl: &mut DefaultEditor) -> Result<u8> {
    loop {
        let input = prompt(rl, "  Strokes: ")?;
        match input.trim().parse::<u8>() {
            Ok(n) if n > 0 && n <= 20 => return Ok(n),
            _ => println!("  Enter a number between 1 and 20."),
        }
    }
}

fn prompt_putts(rl: &mut DefaultEditor, max_strokes: u8) -> Result<u8> {
    loop {
        let input = prompt(rl, "  Putts: ")?;
        match input.trim().parse::<u8>() {
            Ok(n) if n <= max_strokes => return Ok(n),
            _ => println!("  Enter putts (0–{max_strokes})."),
        }
    }
}

fn prompt_fairway(rl: &mut DefaultEditor, par: u8) -> Result<Option<bool>> {
    if par <= 3 {
        return Ok(None);
    }
    let fh = prompt(rl, "  Fairway hit? (y/n/skip): ")?;
    Ok(match fh.trim().to_lowercase().as_str() {
        "y" | "yes" => Some(true),
        "n" | "no" => Some(false),
        _ => None,
    })
}

fn prompt_gir(rl: &mut DefaultEditor, strokes: u8, par: u8) -> Result<Option<bool>> {
    let gir_threshold = par.saturating_sub(2);
    if strokes <= gir_threshold {
        return Ok(Some(true));
    }
    let g = prompt(rl, "  Green in regulation? (y/n/skip): ")?;
    Ok(match g.trim().to_lowercase().as_str() {
        "y" | "yes" => Some(true),
        "n" | "no" => Some(false),
        _ => None,
    })
}

// ─── scorecard ────────────────────────────────────────────────────────────────

fn cmd_scorecard() -> Result<()> {
    let rounds = storage::load_all_rounds()?;
    let round = rounds
        .first()
        .ok_or_else(|| anyhow::anyhow!("No rounds found."))?;
    display::print_scorecard(round);
    let round_stats = RoundStats::from_round(round);
    display::print_round_stats(round, &round_stats);
    Ok(())
}

// ─── finish ───────────────────────────────────────────────────────────────────

async fn cmd_finish() -> Result<()> {
    let mut round = storage::load_active_round()
        .ok_or_else(|| anyhow::anyhow!("No active round found. Start one with 'ai-caddie new'."))?;

    let http = Client::new();
    let round_stats = RoundStats::from_round(&round);

    display::print_scorecard(&round);
    display::print_round_stats(&round, &round_stats);

    finish_round_with(&http, &mut round, &round_stats).await
}

async fn finish_round_with(
    http: &Client,
    round: &mut Round,
    round_stats: &RoundStats,
) -> Result<()> {
    println!("  Generating AI post-round analysis...");
    match ai::analyze_round(http, round, round_stats).await {
        Ok(analysis) => {
            display::print_ai_response("Post-Round Analysis", &analysis);
            round.ai_analysis = Some(analysis);
        }
        Err(e) => display::print_error(&format!("AI analysis unavailable: {e}")),
    }

    round.is_complete = true;
    storage::save_round(round)?;
    display::print_success("Round saved to history.");
    Ok(())
}

// ─── stats ────────────────────────────────────────────────────────────────────

fn cmd_stats() -> Result<()> {
    let rounds = storage::load_all_rounds()?;
    let career = CareerStats::from_rounds(&rounds);
    display::print_career_stats(&career);
    Ok(())
}

// ─── history ─────────────────────────────────────────────────────────────────

fn cmd_history() -> Result<()> {
    let rounds = storage::load_all_rounds()?;
    display::print_round_list(&rounds);
    Ok(())
}

// ─── ask ─────────────────────────────────────────────────────────────────────

async fn cmd_ask(words: &[String]) -> Result<()> {
    if words.is_empty() {
        bail!("Usage: ai-caddie ask <your question>");
    }
    let question = words.join(" ");
    let http = Client::new();
    println!("  Asking AI caddie...");
    let answer = ai::ask(&http, &question).await?;
    display::print_ai_response("AI Caddie", &answer);
    Ok(())
}

// ─── courses ─────────────────────────────────────────────────────────────────

fn cmd_courses() {
    println!();
    for c in ALL_COURSES {
        println!("  {} — {}", c.name, c.location);
        println!(
            "    Par {}  |  Black: {:.1}/{} ({} yds)  |  White: {:.1}/{} ({} yds)",
            c.total_par(),
            c.rating_black,
            c.slope_black,
            c.total_yardage("black"),
            c.rating_white,
            c.slope_white,
            c.total_yardage("white"),
        );
        println!();
    }
}

// ─── Input helpers ─────────────────────────────────────────────────────────────

fn prompt(rl: &mut DefaultEditor, msg: &str) -> Result<String> {
    match rl.readline(msg) {
        Ok(line) => {
            let _ = rl.add_history_entry(&line);
            Ok(line)
        }
        Err(ReadlineError::Interrupted | ReadlineError::Eof) => {
            println!();
            std::process::exit(0);
        }
        Err(e) => Err(e).context("Input error"),
    }
}

fn prompt_or_default(rl: &mut DefaultEditor, msg: &str, default: &str) -> String {
    prompt(rl, msg).unwrap_or_else(|_| default.to_owned())
}
