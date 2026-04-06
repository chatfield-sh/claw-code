use crossterm::style::{Color, Stylize};
use std::fmt::Write as _;

use crate::round::{HoleScore, Round};
use crate::stats::RoundStats;

// ─── Score coloring ────────────────────────────────────────────────────────────

#[must_use]
pub fn score_color(vs_par: i8) -> Color {
    match vs_par {
        i8::MIN..=-2 => Color::Yellow, // Eagle or better
        -1 => Color::Green,            // Birdie
        0 => Color::White,             // Par
        1 => Color::Red,               // Bogey
        _ => Color::DarkRed,           // Double bogey+
    }
}

#[must_use]
pub fn score_symbol(vs_par: i8) -> &'static str {
    match vs_par {
        i8::MIN..=-3 => "◎",
        -2 => "◉",
        -1 => "○",
        0 => "□",
        1 => "▪",
        2 => "▪▪",
        _ => "▪▪▪",
    }
}

/// Format a score relative to par as "+3", "-1", or "E"
#[must_use]
pub fn fmt_vs_par(vs_par: i32) -> String {
    match vs_par.cmp(&0) {
        std::cmp::Ordering::Less => format!("{vs_par}"),
        std::cmp::Ordering::Equal => "E".into(),
        std::cmp::Ordering::Greater => format!("+{vs_par}"),
    }
}

// ─── Scorecard ─────────────────────────────────────────────────────────────────

pub fn print_scorecard(round: &Round) {
    let width = 80;
    println!();
    println!("{}", "═".repeat(width));
    println!(
        "  {}  •  {}  •  {} tees",
        round.course_name, round.player_name, round.tee_color
    );
    println!(
        "  {}  •  HCP index {:.1}  •  Course HCP {}",
        round.date.format("%b %d, %Y"),
        round.handicap_index,
        round.course_handicap()
    );
    println!("{}", "═".repeat(width));

    print_card_rows(round);
    print_card_score_row(round);

    println!("{}", "═".repeat(width));
}

fn print_card_rows(round: &Round) {
    let front_par: u8 = round
        .holes
        .iter()
        .filter(|h| h.hole_number <= 9)
        .map(|h| h.par)
        .sum();
    let back_par: u8 = round
        .holes
        .iter()
        .filter(|h| h.hole_number > 9)
        .map(|h| h.par)
        .sum();
    let total_par: u8 = front_par + back_par;
    let has_back = round.holes.len() > 9;

    // Header row
    print!("  {:>4}  ", "Hole");
    for h in &round.holes {
        print!("{:>3}", h.hole_number);
    }
    if has_back {
        print!("  {:>4}  {:>4}  {:>5}", "Out", "In", "Total");
    } else {
        print!("  {:>4}", "Out");
    }
    println!();

    // Par row
    print!("  {:>4}  ", "Par");
    for h in &round.holes {
        print!("{:>3}", h.par);
    }
    if has_back {
        print!("  {front_par:>4}  {back_par:>4}  {total_par:>5}");
    } else {
        print!("  {front_par:>4}");
    }
    println!();

    // Stroke index row
    print!("  {:>4}  ", "SI");
    for h in &round.holes {
        print!("{:>3}", h.stroke_index);
    }
    println!();

    // Yardage row
    let front_yds: u32 = round
        .holes
        .iter()
        .filter(|h| h.hole_number <= 9)
        .map(|h| u32::from(h.yardage))
        .sum();
    let back_yds: u32 = round
        .holes
        .iter()
        .filter(|h| h.hole_number > 9)
        .map(|h| u32::from(h.yardage))
        .sum();
    print!("  {:>4}  ", "Yds");
    for h in &round.holes {
        print!("{:>3}", h.yardage);
    }
    if has_back {
        let total_yds = front_yds + back_yds;
        print!("  {front_yds:>4}  {back_yds:>4}  {total_yds:>5}");
    } else {
        print!("  {front_yds:>4}");
    }
    println!();

    println!("{}", "─".repeat(80));
}

fn print_card_score_row(round: &Round) {
    let front_par: u8 = round
        .holes
        .iter()
        .filter(|h| h.hole_number <= 9)
        .map(|h| h.par)
        .sum();
    let back_par: u8 = round
        .holes
        .iter()
        .filter(|h| h.hole_number > 9)
        .map(|h| h.par)
        .sum();

    // Score row
    print!("  {:>4}  ", "Score");
    for h in &round.holes {
        if let Some(s) = h.strokes {
            let vs = h.score_vs_par().unwrap_or(0);
            let color = score_color(vs);
            print!("{}", format!("{s:>3}").with(color));
        } else {
            print!("{:>3}", "-");
        }
    }
    let front_score = round.front_nine_score();
    let back_score = round.back_nine_score();
    let total_score = round.total_strokes();
    if round.holes.len() > 9 {
        let fvp = i64::from(front_score) - i64::from(front_par);
        let bvp = i64::from(back_score) - i64::from(back_par);
        let tvp = round.score_vs_par();
        print!(
            "  {:>4}  {:>4}  {:>5}",
            format!("{front_score}({fvp:+})"),
            format!("{back_score}({bvp:+})"),
            format!("{total_score}({tvp:+})"),
        );
    } else if front_score > 0 {
        print!("  {front_score:>4}");
    }
    println!();

    // Putts row
    print!("  {:>4}  ", "Putts");
    for h in &round.holes {
        if let Some(p) = h.putts {
            print!("{p:>3}");
        } else {
            print!("{:>3}", "-");
        }
    }
    println!();
}

// ─── Hole header ───────────────────────────────────────────────────────────────

pub fn print_hole_header(hole: &HoleScore) {
    println!();
    println!(
        "┌─── Hole {} ─── Par {} ─── {} yards ─── Stroke Index {} ─────────────────",
        hole.hole_number, hole.par, hole.yardage, hole.stroke_index
    );
}

// ─── Running score ─────────────────────────────────────────────────────────────

pub fn print_running_score(round: &Round) {
    let played = round.holes_played();
    if played == 0 {
        return;
    }
    let vs_par = round.score_vs_par();
    let color = match vs_par.cmp(&0) {
        std::cmp::Ordering::Less => Color::Green,
        std::cmp::Ordering::Greater => Color::Red,
        std::cmp::Ordering::Equal => Color::White,
    };
    println!(
        "  Running total: {} — {} through {} holes",
        fmt_vs_par(vs_par).with(color),
        round.total_strokes(),
        played
    );
}

// ─── Stats summary ─────────────────────────────────────────────────────────────

pub fn print_round_stats(round: &Round, stats: &RoundStats) {
    println!();
    println!("{}", "─".repeat(50));
    println!("  Round Statistics");
    println!("{}", "─".repeat(50));
    println!(
        "  GIR:         {}/{} ({:.0}%)",
        stats.gir,
        stats.gir_opportunities,
        stats.gir_pct()
    );
    println!(
        "  Fairways:    {}/{} ({:.0}%)",
        stats.fairways_hit,
        stats.fairway_opportunities,
        stats.fir_pct()
    );
    println!(
        "  Avg Putts:   {:.1}  (total: {})",
        stats.avg_putts(),
        stats.total_putts
    );
    println!(
        "  1-Putts:     {}   3-Putts: {}",
        stats.one_putts, stats.three_putts
    );
    println!();
    println!(
        "  Eagles:  {}   Birdies: {}   Pars: {}",
        stats.eagles, stats.birdies, stats.pars
    );
    println!(
        "  Bogeys:  {}   Doubles: {}   Triple+: {}",
        stats.bogeys, stats.double_bogeys, stats.triple_plus
    );
    println!();
    println!(
        "  Gross score:    {}  ({:+})",
        round.total_strokes(),
        round.score_vs_par()
    );
    println!("  Course HCP:     {}", round.course_handicap());
    println!("  Net vs par:     {:+}", round.net_score_vs_par());
    println!("  HCP diff:       {:.1}", round.handicap_differential());
    println!("{}", "─".repeat(50));
}

// ─── Career stats ──────────────────────────────────────────────────────────────

pub fn print_career_stats(cs: &crate::stats::CareerStats) {
    println!();
    println!("{}", "═".repeat(50));
    println!("  Career Statistics ({} rounds)", cs.rounds_played);
    println!("{}", "═".repeat(50));
    if cs.rounds_played == 0 {
        println!("  No completed rounds yet. Play your first round!");
        return;
    }
    println!(
        "  Scoring avg:    {:.1}  ({:+.1} vs par)",
        cs.scoring_average(),
        cs.avg_vs_par()
    );
    if let Some(best) = cs.best_gross {
        println!("  Best gross:     {best}");
    }
    if let Some(worst) = cs.worst_gross {
        println!("  Worst gross:    {worst}");
    }
    println!("  Handicap index: {:.1}", cs.handicap_index());
    println!();
    println!("  GIR:            {:.0}%", cs.career_gir_pct());
    println!("  Fairways hit:   {:.0}%", cs.career_fir_pct());
    println!("  Avg putts:      {:.2}", cs.career_avg_putts());
    println!();
    println!(
        "  Birdies/round:  {:.1}",
        f64::from(cs.total_birdies) / f64::from(cs.rounds_played)
    );
    println!("  Eagles total:   {}", cs.total_eagles);
    println!("{}", "═".repeat(50));
}

// ─── Round history list ────────────────────────────────────────────────────────

pub fn print_round_list(rounds: &[Round]) {
    if rounds.is_empty() {
        println!("  No rounds found. Start one with: ai-caddie new");
        return;
    }
    println!();
    println!("{}", "─".repeat(70));
    println!(
        "  {:<4}  {:<12}  {:<32}  {:>6}  {:>5}",
        "No.", "Date", "Course", "Score", "vs Par"
    );
    println!("{}", "─".repeat(70));
    for (i, r) in rounds.iter().enumerate() {
        if r.is_complete {
            let vp = r.score_vs_par();
            let color = match vp.cmp(&0) {
                std::cmp::Ordering::Less => Color::Green,
                std::cmp::Ordering::Greater => Color::Red,
                std::cmp::Ordering::Equal => Color::White,
            };
            println!(
                "  {:<4}  {:<12}  {:<32}  {:>6}  {:>5}",
                i + 1,
                r.date.format("%Y-%m-%d"),
                truncate(&r.course_name, 32),
                r.total_strokes(),
                fmt_vs_par(vp).with(color),
            );
        } else {
            println!(
                "  {:<4}  {:<12}  {:<32}  {:<6}  {:>5}  [IN PROGRESS]",
                i + 1,
                r.date.format("%Y-%m-%d"),
                truncate(&r.course_name, 32),
                format!("{}/{}", r.total_strokes(), r.holes_played()),
                ""
            );
        }
    }
    println!("{}", "─".repeat(70));
}

// ─── AI response box ──────────────────────────────────────────────────────────

pub fn print_ai_response(label: &str, text: &str) {
    println!();
    println!(
        "  ╔═ {label} {}",
        "═".repeat(56usize.saturating_sub(label.len() + 3))
    );
    for line in textwrap(text, 72) {
        println!("  ║  {line}");
    }
    println!("  ╚{}", "═".repeat(59));
    println!();
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

fn truncate(s: &str, max: usize) -> String {
    if s.len() <= max {
        s.to_owned()
    } else {
        format!("{}…", &s[..max.saturating_sub(1)])
    }
}

fn textwrap(text: &str, width: usize) -> Vec<String> {
    let mut lines = Vec::new();
    for paragraph in text.split('\n') {
        if paragraph.is_empty() {
            lines.push(String::new());
            continue;
        }
        let mut current = String::new();
        for word in paragraph.split_whitespace() {
            if current.is_empty() {
                current.push_str(word);
            } else if current.len() + 1 + word.len() <= width {
                current.push(' ');
                current.push_str(word);
            } else {
                lines.push(current.clone());
                current.clear();
                current.push_str(word);
            }
        }
        if !current.is_empty() {
            lines.push(current);
        }
    }
    lines
}

// ─── Prompt helpers ────────────────────────────────────────────────────────────

pub fn print_error(msg: &str) {
    eprintln!("  [ERROR] {msg}");
}

pub fn print_success(msg: &str) {
    println!("{}", format!("  ✓ {msg}").with(Color::Green));
}

pub fn separator() {
    println!("{}", "─".repeat(60));
}

/// Formatted hole score symbol with color
#[must_use]
pub fn colored_score_cell(hole: &HoleScore) -> String {
    if let (Some(s), Some(vs)) = (hole.strokes, hole.score_vs_par()) {
        let sym = score_symbol(vs);
        let color = score_color(vs);
        let mut buf = String::new();
        let _ = write!(buf, "{}", format!("{s}{sym}").with(color));
        buf
    } else {
        "  -".to_owned()
    }
}
