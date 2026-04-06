use chrono::{DateTime, Local};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ShotResult {
    Fairway,
    Rough,
    Bunker,
    Water,
    ObOrLost,
    Green,
    Holed,
}

impl std::fmt::Display for ShotResult {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Fairway => write!(f, "Fairway"),
            Self::Rough => write!(f, "Rough"),
            Self::Bunker => write!(f, "Bunker"),
            Self::Water => write!(f, "Water hazard"),
            Self::ObOrLost => write!(f, "OB / Lost ball"),
            Self::Green => write!(f, "Green"),
            Self::Holed => write!(f, "In the hole!"),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Shot {
    pub club: String,
    pub distance_yards: Option<u16>,
    pub result: ShotResult,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HoleScore {
    pub hole_number: u8,
    pub par: u8,
    pub yardage: u16,
    /// Stroke index: 1 = hardest, 18 = easiest
    pub stroke_index: u8,
    pub strokes: Option<u8>,
    pub putts: Option<u8>,
    /// None for par-3s (no fairway shot)
    pub fairway_hit: Option<bool>,
    /// Green in regulation
    pub gir: Option<bool>,
    pub shots: Vec<Shot>,
    pub ai_tip: Option<String>,
}

impl HoleScore {
    /// Net score relative to par (negative = under par)
    #[must_use]
    pub fn score_vs_par(&self) -> Option<i8> {
        self.strokes
            .and_then(|s| i8::try_from(i16::from(s) - i16::from(self.par)).ok())
    }

    #[must_use]
    pub fn score_name(&self) -> Option<&'static str> {
        self.score_vs_par().map(|diff| match diff {
            i8::MIN..=-3 => "Albatross",
            -2 => "Eagle",
            -1 => "Birdie",
            0 => "Par",
            1 => "Bogey",
            2 => "Double Bogey",
            3 => "Triple Bogey",
            _ => "Snowman+",
        })
    }

    /// Handicap strokes received on this hole given a course handicap
    #[must_use]
    pub fn strokes_received(&self, course_handicap: u8) -> u8 {
        // A handicap of 18 gets one stroke on every hole.
        // A handicap of 20 gets two strokes on the two hardest holes.
        let base = course_handicap / 18;
        let extra = course_handicap % 18;
        if self.stroke_index <= extra {
            base + 1
        } else {
            base
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Weather {
    pub wind_speed_mph: u8,
    pub wind_direction: String,
    pub temperature_f: i16,
    pub conditions: String,
}

impl std::fmt::Display for Weather {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "{}°F, {} mph wind from {}, {}",
            self.temperature_f, self.wind_speed_mph, self.wind_direction, self.conditions
        )
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Round {
    pub id: String,
    pub course_name: String,
    pub date: DateTime<Local>,
    pub player_name: String,
    pub handicap_index: f64,
    pub tee_color: String,
    pub course_rating: f64,
    pub slope_rating: u16,
    pub holes: Vec<HoleScore>,
    pub weather: Option<Weather>,
    pub ai_analysis: Option<String>,
    pub is_complete: bool,
}

impl Round {
    #[must_use]
    pub fn total_strokes(&self) -> u32 {
        self.holes
            .iter()
            .filter_map(|h| h.strokes)
            .map(u32::from)
            .sum()
    }

    #[must_use]
    pub fn total_par(&self) -> u32 {
        self.holes
            .iter()
            .filter(|h| h.strokes.is_some())
            .map(|h| u32::from(h.par))
            .sum()
    }

    #[must_use]
    pub fn score_vs_par(&self) -> i32 {
        let diff = i64::from(self.total_strokes()) - i64::from(self.total_par());
        i32::try_from(diff).unwrap_or(0)
    }

    #[must_use]
    pub fn holes_played(&self) -> usize {
        self.holes.iter().filter(|h| h.strokes.is_some()).count()
    }

    /// World Handicap System course handicap formula
    #[must_use]
    pub fn course_handicap(&self) -> i32 {
        let par: u32 = self.holes.iter().map(|h| u32::from(h.par)).sum();
        let ch = self.handicap_index * (f64::from(self.slope_rating) / 113.0)
            + (self.course_rating - f64::from(par));
        // Course handicap is bounded to a small range; truncation is intentional.
        #[allow(clippy::cast_possible_truncation)]
        let result = ch.round() as i32;
        result
    }

    /// Handicap differential for this round (used to update handicap index)
    #[must_use]
    pub fn handicap_differential(&self) -> f64 {
        (f64::from(self.total_strokes()) - self.course_rating) * 113.0
            / f64::from(self.slope_rating)
    }

    /// Net score vs par after applying course handicap
    #[must_use]
    pub fn net_score_vs_par(&self) -> i32 {
        self.score_vs_par() - self.course_handicap()
    }

    #[must_use]
    pub fn front_nine_score(&self) -> u32 {
        self.holes
            .iter()
            .filter(|h| h.hole_number <= 9)
            .filter_map(|h| h.strokes)
            .map(u32::from)
            .sum()
    }

    #[must_use]
    pub fn back_nine_score(&self) -> u32 {
        self.holes
            .iter()
            .filter(|h| h.hole_number > 9)
            .filter_map(|h| h.strokes)
            .map(u32::from)
            .sum()
    }
}
