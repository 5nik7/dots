static const char norm_fg[] = "#d6e9ff";
static const char norm_bg[] = "#2E3C5B";
static const char norm_border[] = "#374B72";

static const char sel_fg[] = "#d6e9ff";
static const char sel_bg[] = "#00FFCC";
static const char sel_border[] = "#d6e9ff";

static const char urg_fg[] = "#d6e9ff";
static const char urg_bg[] = "#EB6F92";
static const char urg_border[] = "#EB6F92";

static const char *colors[][3]      = {
    /*               fg           bg         border                         */
    [SchemeNorm] = { norm_fg,     norm_bg,   norm_border }, // unfocused wins
    [SchemeSel]  = { sel_fg,      sel_bg,    sel_border },  // the focused win
    [SchemeUrg] =  { urg_fg,      urg_bg,    urg_border },
};
