use crate::round::Round;

/// Aggregated statistics for a single round
#[derive(Debug, Default)]
pub struct RoundStats {
    pub gir: u8,
    pub gir_opportunities: u8,
    pub fairways_hit: u8,
    pub fairway_opportunities: u8,
    pub total_putts: u16,
    pub holes_with_putts: u8,
    pub eagles: u8,
    pub birdies: u8,
    pub pars: u8,
    pub bogeys: u8,
    pub double_bogeys: u8,
    pub triple_plus: u8,
    pub three_putts: u8,
    pub one_putts: u8,
}

impl RoundStats {
    #[must_use]
    pub fn from_round(round: &Round) -> Self {
        let mut stats = Self::default();
        for hole in round.holes.iter().filter(|h| h.strokes.is_some()) {
            // GIR
            stats.gir_opportunities += 1;
            if hole.gir == Some(true) {
                stats.gir += 1;
            }

            // FIR (only for par 4 and 5)
            if hole.par > 3 {
                stats.fairway_opportunities += 1;
                if hole.fairway_hit == Some(true) {
                    stats.fairways_hit += 1;
                }
            }

            // Putts
            if let Some(p) = hole.putts {
                stats.total_putts += u16::from(p);
                stats.holes_with_putts += 1;
                if p == 1 {
                    stats.one_putts += 1;
                } else if p >= 3 {
                    stats.three_putts += 1;
                }
            }

            // Score categories
            match hole.score_vs_par() {
                Some(d) if d <= -2 => stats.eagles += 1,
                Some(-1) => stats.birdies += 1,
                Some(0) => stats.pars += 1,
                Some(1) => stats.bogeys += 1,
                Some(2) => stats.double_bogeys += 1,
                Some(d) if d >= 3 => stats.triple_plus += 1,
                _ => {}
            }
        }
        stats
    }

    #[must_use]
    pub fn gir_pct(&self) -> f64 {
        if self.gir_opportunities == 0 {
            return 0.0;
        }
        f64::from(self.gir) / f64::from(self.gir_opportunities) * 100.0
    }

    #[must_use]
    pub fn fir_pct(&self) -> f64 {
        if self.fairway_opportunities == 0 {
            return 0.0;
        }
        f64::from(self.fairways_hit) / f64::from(self.fairway_opportunities) * 100.0
    }

    #[must_use]
    pub fn avg_putts(&self) -> f64 {
        if self.holes_with_putts == 0 {
            return 0.0;
        }
        f64::from(self.total_putts) / f64::from(self.holes_with_putts)
    }
}

/// Lifetime statistics across multiple rounds
#[derive(Debug, Default)]
pub struct CareerStats {
    pub rounds_played: u32,
    pub total_strokes: u64,
    pub total_par: u64,
    pub best_gross: Option<u32>,
    pub worst_gross: Option<u32>,
    pub best_differential: Option<f64>,
    pub total_birdies: u32,
    pub total_eagles: u32,
    pub total_gir: u32,
    pub total_gir_opportunities: u32,
    pub total_fairways: u32,
    pub total_fairway_opportunities: u32,
    pub total_putts: u64,
    pub total_holes_with_putts: u32,
    pub handicap_differentials: Vec<f64>,
}

impl CareerStats {
    #[must_use]
    pub fn from_rounds(rounds: &[Round]) -> Self {
        let mut cs = Self::default();
        for round in rounds.iter().filter(|r| r.is_complete) {
            cs.rounds_played += 1;
            cs.total_strokes += u64::from(round.total_strokes());
            cs.total_par += u64::from(round.total_par());

            let gross = round.total_strokes();
            cs.best_gross = Some(cs.best_gross.map_or(gross, |b: u32| b.min(gross)));
            cs.worst_gross = Some(cs.worst_gross.map_or(gross, |w: u32| w.max(gross)));

            let diff = round.handicap_differential();
            cs.best_differential = Some(cs.best_differential.map_or(diff, |b: f64| b.min(diff)));
            cs.handicap_differentials.push(diff);

            let rs = RoundStats::from_round(round);
            cs.total_birdies += u32::from(rs.birdies);
            cs.total_eagles += u32::from(rs.eagles);
            cs.total_gir += u32::from(rs.gir);
            cs.total_gir_opportunities += u32::from(rs.gir_opportunities);
            cs.total_fairways += u32::from(rs.fairways_hit);
            cs.total_fairway_opportunities += u32::from(rs.fairway_opportunities);
            cs.total_putts += u64::from(rs.total_putts);
            cs.total_holes_with_putts += u32::from(rs.holes_with_putts);
        }
        cs
    }

    #[must_use]
    pub fn scoring_average(&self) -> f64 {
        if self.rounds_played == 0 {
            return 0.0;
        }
        // total_strokes fits in f64 precisely up to ~9 quadrillion
        #[allow(clippy::cast_precision_loss)]
        let strokes = self.total_strokes as f64;
        strokes / f64::from(self.rounds_played)
    }

    #[must_use]
    pub fn avg_vs_par(&self) -> f64 {
        if self.rounds_played == 0 {
            return 0.0;
        }
        #[allow(clippy::cast_precision_loss)]
        let diff = (self.total_strokes as f64) - (self.total_par as f64);
        diff / f64::from(self.rounds_played)
    }

    #[must_use]
    pub fn career_gir_pct(&self) -> f64 {
        if self.total_gir_opportunities == 0 {
            return 0.0;
        }
        f64::from(self.total_gir) / f64::from(self.total_gir_opportunities) * 100.0
    }

    #[must_use]
    pub fn career_fir_pct(&self) -> f64 {
        if self.total_fairway_opportunities == 0 {
            return 0.0;
        }
        f64::from(self.total_fairways) / f64::from(self.total_fairway_opportunities) * 100.0
    }

    #[must_use]
    pub fn career_avg_putts(&self) -> f64 {
        if self.total_holes_with_putts == 0 {
            return 0.0;
        }
        #[allow(clippy::cast_precision_loss)]
        let putts = self.total_putts as f64;
        putts / f64::from(self.total_holes_with_putts)
    }

    /// Handicap index based on best 8 of last 20 differentials (simplified WHS)
    #[must_use]
    pub fn handicap_index(&self) -> f64 {
        let window: Vec<f64> = self
            .handicap_differentials
            .iter()
            .rev()
            .take(20)
            .copied()
            .collect();

        if window.is_empty() {
            return 0.0;
        }

        let best_count = match window.len() {
            1..=5 => 1,
            6..=8 => 2,
            9..=11 => 3,
            12..=14 => 4,
            15..=16 => 5,
            17..=18 => 6,
            19 => 7,
            _ => 8,
        };

        let mut sorted = window.clone();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        let total: f64 = sorted.iter().take(best_count).sum();
        #[allow(clippy::cast_precision_loss)]
        let avg = total / best_count as f64;
        (avg * 0.96 * 10.0).round() / 10.0
    }
}
