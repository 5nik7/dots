static const char norm_fg[] = "#E4F0FF";
static const char norm_bg[] = "#334775";
static const char norm_border[] = "#49608D";

static const char sel_fg[] = "#E4F0FF";
static const char sel_bg[] = "#00FFCC";
static const char sel_border[] = "#E4F0FF";

static const char urg_fg[] = "#E4F0FF";
static const char urg_bg[] = "#FF5673";
static const char urg_border[] = "#FF5673";

static const char *colors[][3]      = {
    /*               fg           bg         border                         */
    [SchemeNorm] = { norm_fg,     norm_bg,   norm_border }, // unfocused wins
    [SchemeSel]  = { sel_fg,      sel_bg,    sel_border },  // the focused win
    [SchemeUrg] =  { urg_fg,      urg_bg,    urg_border },
};
