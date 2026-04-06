use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HoleInfo {
    pub number: u8,
    pub par: u8,
    /// Stroke index 1–18 (1 = hardest)
    pub stroke_index: u8,
    pub yardage_black: u16,
    pub yardage_blue: u16,
    pub yardage_white: u16,
    pub yardage_red: u16,
    pub description: &'static str,
}

#[derive(Debug, Clone)]
pub struct Course {
    pub name: &'static str,
    pub location: &'static str,
    pub rating_black: f64,
    pub slope_black: u16,
    pub rating_blue: f64,
    pub slope_blue: u16,
    pub rating_white: f64,
    pub slope_white: u16,
    pub rating_red: f64,
    pub slope_red: u16,
    pub holes: &'static [HoleInfo],
}

impl Course {
    #[must_use]
    pub fn rating_for_tee(&self, tee: &str) -> f64 {
        match tee.to_lowercase().as_str() {
            "black" | "tips" => self.rating_black,
            "blue" | "back" => self.rating_blue,
            "red" | "forward" | "women" => self.rating_red,
            _ => self.rating_white,
        }
    }

    #[must_use]
    pub fn slope_for_tee(&self, tee: &str) -> u16 {
        match tee.to_lowercase().as_str() {
            "black" | "tips" => self.slope_black,
            "blue" | "back" => self.slope_blue,
            "red" | "forward" | "women" => self.slope_red,
            _ => self.slope_white,
        }
    }

    #[must_use]
    pub fn yardage_for_tee(hole: &HoleInfo, tee: &str) -> u16 {
        match tee.to_lowercase().as_str() {
            "black" | "tips" => hole.yardage_black,
            "blue" | "back" => hole.yardage_blue,
            "red" | "forward" | "women" => hole.yardage_red,
            _ => hole.yardage_white,
        }
    }

    #[must_use]
    pub fn total_par(&self) -> u8 {
        self.holes.iter().map(|h| h.par).sum()
    }

    #[must_use]
    pub fn total_yardage(&self, tee: &str) -> u32 {
        self.holes
            .iter()
            .map(|h| u32::from(Self::yardage_for_tee(h, tee)))
            .sum()
    }
}

// ─── Augusta National ─────────────────────────────────────────────────────────

static AUGUSTA_HOLES: &[HoleInfo] = &[
    HoleInfo { number: 1,  par: 4, stroke_index: 9,  yardage_black: 445, yardage_blue: 425, yardage_white: 400, yardage_red: 365, description: "Tea Olive – Dogleg right, uphill approach to elevated green with false front" },
    HoleInfo { number: 2,  par: 5, stroke_index: 3,  yardage_black: 575, yardage_blue: 555, yardage_white: 520, yardage_red: 490, description: "Pink Dogwood – Uphill par 5, three bunkers guard the two-tiered green" },
    HoleInfo { number: 3,  par: 4, stroke_index: 15, yardage_black: 350, yardage_blue: 325, yardage_white: 305, yardage_red: 280, description: "Flowering Peach – Short par 4; deceptive approach to shallow green" },
    HoleInfo { number: 4,  par: 3, stroke_index: 7,  yardage_black: 240, yardage_blue: 215, yardage_white: 185, yardage_red: 150, description: "Flowering Crab Apple – Long par 3 with deep green and tiered putting surface" },
    HoleInfo { number: 5,  par: 4, stroke_index: 5,  yardage_black: 495, yardage_blue: 460, yardage_white: 435, yardage_red: 395, description: "Magnolia – Long par 4; two bunkers frame the green on a perched site" },
    HoleInfo { number: 6,  par: 3, stroke_index: 13, yardage_black: 180, yardage_blue: 165, yardage_white: 145, yardage_red: 120, description: "Juniper – Downhill par 3; any miss leaves a difficult recovery" },
    HoleInfo { number: 7,  par: 4, stroke_index: 11, yardage_black: 450, yardage_blue: 425, yardage_white: 405, yardage_red: 370, description: "Pampas – Dogleg left; approach over bunkers to a severely sloped green" },
    HoleInfo { number: 8,  par: 5, stroke_index: 1,  yardage_black: 570, yardage_blue: 545, yardage_white: 510, yardage_red: 470, description: "Yellow Jasmine – Big dogleg right; split-level green behind Raes Creek tributary" },
    HoleInfo { number: 9,  par: 4, stroke_index: 17, yardage_black: 460, yardage_blue: 435, yardage_white: 415, yardage_red: 385, description: "Carolina Cherry – Blind tee shot then downhill approach to a green that slopes front to back" },
    HoleInfo { number: 10, par: 4, stroke_index: 2,  yardage_black: 495, yardage_blue: 470, yardage_white: 445, yardage_red: 410, description: "Camellia – Steep downhill par 4 through a tree chute; most dramatic tee shot on the course" },
    HoleInfo { number: 11, par: 4, stroke_index: 6,  yardage_black: 505, yardage_blue: 480, yardage_white: 455, yardage_red: 420, description: "White Dogwood – Opening hole of Amen Corner; Raes Creek guards the left of the green" },
    HoleInfo { number: 12, par: 3, stroke_index: 16, yardage_black: 155, yardage_blue: 145, yardage_white: 130, yardage_red: 100, description: "Golden Bell – Short but treacherous par 3 over Raes Creek with swirling winds" },
    HoleInfo { number: 13, par: 5, stroke_index: 8,  yardage_black: 510, yardage_blue: 490, yardage_white: 465, yardage_red: 435, description: "Azalea – Classic Amen Corner par 5; creek guards the green on a reachable hole" },
    HoleInfo { number: 14, par: 4, stroke_index: 14, yardage_black: 440, yardage_blue: 415, yardage_white: 390, yardage_red: 360, description: "Chinese Fir – Flat par 4 with a wildly undulating green; impossible two-putt from wrong spot" },
    HoleInfo { number: 15, par: 5, stroke_index: 4,  yardage_black: 550, yardage_blue: 530, yardage_white: 500, yardage_red: 470, description: "Firethorn – Reachable par 5; pond in front of the green demands a precise lay-up or bold second" },
    HoleInfo { number: 16, par: 3, stroke_index: 12, yardage_black: 170, yardage_blue: 155, yardage_white: 140, yardage_red: 115, description: "Redbud – Over a pond to a long green; Tiger's 2005 chip-in spot" },
    HoleInfo { number: 17, par: 4, stroke_index: 10, yardage_black: 440, yardage_blue: 420, yardage_white: 400, yardage_red: 365, description: "Nandina – Demanding approach over a bunker cluster to a small, severely sloped green" },
    HoleInfo { number: 18, par: 4, stroke_index: 18, yardage_black: 465, yardage_blue: 440, yardage_white: 415, yardage_red: 385, description: "Holly – Uphill dogleg left; approach between two bunkers to the iconic green below the clubhouse" },
];

pub static AUGUSTA_NATIONAL: Course = Course {
    name: "Augusta National Golf Club",
    location: "Augusta, GA",
    rating_black: 76.2,
    slope_black: 148,
    rating_blue: 74.1,
    slope_blue: 140,
    rating_white: 71.7,
    slope_white: 133,
    rating_red: 68.5,
    slope_red: 124,
    holes: AUGUSTA_HOLES,
};

// ─── Pebble Beach ─────────────────────────────────────────────────────────────

static PEBBLE_HOLES: &[HoleInfo] = &[
    HoleInfo {
        number: 1,
        par: 4,
        stroke_index: 9,
        yardage_black: 380,
        yardage_blue: 362,
        yardage_white: 345,
        yardage_red: 320,
        description: "Opening hole – Gentle dogleg left along the cliff edge",
    },
    HoleInfo {
        number: 2,
        par: 5,
        stroke_index: 3,
        yardage_black: 502,
        yardage_blue: 484,
        yardage_white: 460,
        yardage_red: 430,
        description: "Short par 5 reachable in two; tree-lined fairway",
    },
    HoleInfo {
        number: 3,
        par: 4,
        stroke_index: 13,
        yardage_black: 390,
        yardage_blue: 372,
        yardage_white: 350,
        yardage_red: 315,
        description: "Ocean views begin; approach to a plateau green",
    },
    HoleInfo {
        number: 4,
        par: 4,
        stroke_index: 7,
        yardage_black: 331,
        yardage_blue: 317,
        yardage_white: 300,
        yardage_red: 275,
        description: "Drivable par 4; risk/reward off the tee",
    },
    HoleInfo {
        number: 5,
        par: 3,
        stroke_index: 15,
        yardage_black: 188,
        yardage_blue: 176,
        yardage_white: 160,
        yardage_red: 130,
        description: "Elevated tee shot to a green framed by the ocean",
    },
    HoleInfo {
        number: 6,
        par: 5,
        stroke_index: 5,
        yardage_black: 523,
        yardage_blue: 507,
        yardage_white: 485,
        yardage_red: 455,
        description: "Fairway narrows at the cliffside; stunning coastal views",
    },
    HoleInfo {
        number: 7,
        par: 3,
        stroke_index: 17,
        yardage_black: 106,
        yardage_blue: 100,
        yardage_white: 92,
        yardage_red: 78,
        description:
            "Shortest hole on the course; tiny green on a rocky bluff above Stillwater Cove",
    },
    HoleInfo {
        number: 8,
        par: 4,
        stroke_index: 1,
        yardage_black: 428,
        yardage_blue: 411,
        yardage_white: 390,
        yardage_red: 355,
        description: "Blind tee shot over a chasm; one of golf's great second shots",
    },
    HoleInfo {
        number: 9,
        par: 4,
        stroke_index: 11,
        yardage_black: 466,
        yardage_blue: 450,
        yardage_white: 425,
        yardage_red: 390,
        description: "Long par 4 along Stillwater Cove with OB right",
    },
    HoleInfo {
        number: 10,
        par: 4,
        stroke_index: 2,
        yardage_black: 446,
        yardage_blue: 426,
        yardage_white: 400,
        yardage_red: 365,
        description: "Dogleg left; approach to a green perched at the ocean's edge",
    },
    HoleInfo {
        number: 11,
        par: 4,
        stroke_index: 6,
        yardage_black: 380,
        yardage_blue: 362,
        yardage_white: 340,
        yardage_red: 305,
        description: "Short par 4; trees right, ocean left, precision required",
    },
    HoleInfo {
        number: 12,
        par: 3,
        stroke_index: 16,
        yardage_black: 202,
        yardage_blue: 190,
        yardage_white: 175,
        yardage_red: 145,
        description: "Long par 3 along the rocky Pacific coastline",
    },
    HoleInfo {
        number: 13,
        par: 4,
        stroke_index: 10,
        yardage_black: 392,
        yardage_blue: 374,
        yardage_white: 355,
        yardage_red: 320,
        description: "Dogleg right; cross-wind approach to a tight green",
    },
    HoleInfo {
        number: 14,
        par: 5,
        stroke_index: 4,
        yardage_black: 580,
        yardage_blue: 562,
        yardage_white: 540,
        yardage_red: 505,
        description: "Longest hole; back up into the hills with two massive dunes",
    },
    HoleInfo {
        number: 15,
        par: 4,
        stroke_index: 8,
        yardage_black: 397,
        yardage_blue: 379,
        yardage_white: 360,
        yardage_red: 325,
        description: "Drive between mature pines; approach to a sloped green",
    },
    HoleInfo {
        number: 16,
        par: 4,
        stroke_index: 12,
        yardage_black: 403,
        yardage_blue: 385,
        yardage_white: 365,
        yardage_red: 330,
        description: "Dogleg right near the ocean; risk/reward from tee",
    },
    HoleInfo {
        number: 17,
        par: 3,
        stroke_index: 14,
        yardage_black: 208,
        yardage_blue: 195,
        yardage_white: 178,
        yardage_red: 150,
        description:
            "Tom Watson's legendary hole; green surrounded on three sides by Stillwater Cove",
    },
    HoleInfo {
        number: 18,
        par: 5,
        stroke_index: 18,
        yardage_black: 543,
        yardage_blue: 525,
        yardage_white: 500,
        yardage_red: 465,
        description: "Jack Nicklaus's 1-iron; closing par 5 hugging the ocean all the way home",
    },
];

pub static PEBBLE_BEACH: Course = Course {
    name: "Pebble Beach Golf Links",
    location: "Pebble Beach, CA",
    rating_black: 75.5,
    slope_black: 145,
    rating_blue: 73.8,
    slope_blue: 139,
    rating_white: 71.9,
    slope_white: 132,
    rating_red: 69.0,
    slope_red: 122,
    holes: PEBBLE_HOLES,
};

// ─── Generic Municipal Course ─────────────────────────────────────────────────

static MUNICIPAL_HOLES: &[HoleInfo] = &[
    HoleInfo {
        number: 1,
        par: 4,
        stroke_index: 7,
        yardage_black: 410,
        yardage_blue: 390,
        yardage_white: 370,
        yardage_red: 330,
        description: "Opening hole – Wide fairway, flat green, good warmup hole",
    },
    HoleInfo {
        number: 2,
        par: 5,
        stroke_index: 3,
        yardage_black: 530,
        yardage_blue: 510,
        yardage_white: 490,
        yardage_red: 455,
        description: "Reachable par 5 with a slight dogleg right",
    },
    HoleInfo {
        number: 3,
        par: 3,
        stroke_index: 15,
        yardage_black: 175,
        yardage_blue: 160,
        yardage_white: 145,
        yardage_red: 120,
        description: "Short par 3 over a pond to a peninsula green",
    },
    HoleInfo {
        number: 4,
        par: 4,
        stroke_index: 5,
        yardage_black: 440,
        yardage_blue: 420,
        yardage_white: 400,
        yardage_red: 365,
        description: "Tight driving hole with trees both sides",
    },
    HoleInfo {
        number: 5,
        par: 4,
        stroke_index: 11,
        yardage_black: 360,
        yardage_blue: 340,
        yardage_white: 320,
        yardage_red: 290,
        description: "Short par 4 – tempting to drive the green",
    },
    HoleInfo {
        number: 6,
        par: 3,
        stroke_index: 17,
        yardage_black: 155,
        yardage_blue: 140,
        yardage_white: 125,
        yardage_red: 100,
        description: "Downhill par 3; club down",
    },
    HoleInfo {
        number: 7,
        par: 5,
        stroke_index: 1,
        yardage_black: 560,
        yardage_blue: 540,
        yardage_white: 515,
        yardage_red: 480,
        description: "Signature hole – double dogleg par 5, big bunker complex",
    },
    HoleInfo {
        number: 8,
        par: 4,
        stroke_index: 9,
        yardage_black: 420,
        yardage_blue: 400,
        yardage_white: 380,
        yardage_red: 345,
        description: "Dogleg left; bunker at the corner demands a carry",
    },
    HoleInfo {
        number: 9,
        par: 4,
        stroke_index: 13,
        yardage_black: 390,
        yardage_blue: 370,
        yardage_white: 350,
        yardage_red: 315,
        description: "Closing front nine – uphill approach to an elevated green",
    },
    HoleInfo {
        number: 10,
        par: 4,
        stroke_index: 4,
        yardage_black: 445,
        yardage_blue: 425,
        yardage_white: 405,
        yardage_red: 370,
        description: "Back nine opens with a long par 4, water right",
    },
    HoleInfo {
        number: 11,
        par: 3,
        stroke_index: 16,
        yardage_black: 190,
        yardage_blue: 175,
        yardage_white: 155,
        yardage_red: 130,
        description: "Long par 3 into the prevailing wind",
    },
    HoleInfo {
        number: 12,
        par: 5,
        stroke_index: 2,
        yardage_black: 545,
        yardage_blue: 525,
        yardage_white: 500,
        yardage_red: 465,
        description: "Risk/reward par 5; creek crosses fairway 100 yards out",
    },
    HoleInfo {
        number: 13,
        par: 4,
        stroke_index: 8,
        yardage_black: 415,
        yardage_blue: 395,
        yardage_white: 375,
        yardage_red: 340,
        description: "Dogleg right with a blind tee shot over a hill",
    },
    HoleInfo {
        number: 14,
        par: 4,
        stroke_index: 6,
        yardage_black: 430,
        yardage_blue: 410,
        yardage_white: 390,
        yardage_red: 355,
        description: "Long par 4 into the wind; big green with tricky slopes",
    },
    HoleInfo {
        number: 15,
        par: 5,
        stroke_index: 14,
        yardage_black: 510,
        yardage_blue: 490,
        yardage_white: 465,
        yardage_red: 435,
        description: "Shorter par 5; go for it in two from the right side",
    },
    HoleInfo {
        number: 16,
        par: 3,
        stroke_index: 18,
        yardage_black: 145,
        yardage_blue: 130,
        yardage_white: 115,
        yardage_red: 95,
        description: "Easiest hole – short par 3, hit and make birdie",
    },
    HoleInfo {
        number: 17,
        par: 4,
        stroke_index: 10,
        yardage_black: 400,
        yardage_blue: 380,
        yardage_white: 360,
        yardage_red: 325,
        description: "Dogleg left; approach through a narrow opening",
    },
    HoleInfo {
        number: 18,
        par: 4,
        stroke_index: 12,
        yardage_black: 435,
        yardage_blue: 415,
        yardage_white: 395,
        yardage_red: 360,
        description: "Finishing hole – uphill par 4 with water short of the green",
    },
];

pub static MUNICIPAL: Course = Course {
    name: "Riverside Municipal Golf Course",
    location: "Anytown, USA",
    rating_black: 72.8,
    slope_black: 132,
    rating_blue: 71.2,
    slope_blue: 128,
    rating_white: 69.8,
    slope_white: 122,
    rating_red: 67.5,
    slope_red: 116,
    holes: MUNICIPAL_HOLES,
};

// ─── Course registry ──────────────────────────────────────────────────────────

pub static ALL_COURSES: &[&Course] = &[&AUGUSTA_NATIONAL, &PEBBLE_BEACH, &MUNICIPAL];
