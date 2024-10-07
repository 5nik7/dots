static const char norm_fg[] = "#e4f0ff";
static const char norm_bg[] = "#142444";
static const char norm_border[] = "#334775";

static const char sel_fg[] = "#e4f0ff";
static const char sel_bg[] = "#4C5370";
static const char sel_border[] = "#e4f0ff";

static const char urg_fg[] = "#e4f0ff";
static const char urg_bg[] = "#907277";
static const char urg_border[] = "#907277";

static const char *colors[][3]      = {
    /*               fg           bg         border                         */
    [SchemeNorm] = { norm_fg,     norm_bg,   norm_border }, // unfocused wins
    [SchemeSel]  = { sel_fg,      sel_bg,    sel_border },  // the focused win
    [SchemeUrg] =  { urg_fg,      urg_bg,    urg_border },
};
