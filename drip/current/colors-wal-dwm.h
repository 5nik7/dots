static const char norm_fg[] = "#fdffff";
static const char norm_bg[] = "#181e21";
static const char norm_border[] = "#2c383e";

static const char sel_fg[] = "#fdffff";
static const char sel_bg[] = "#7999aa";
static const char sel_border[] = "#fdffff";

static const char urg_fg[] = "#fdffff";
static const char urg_bg[] = "#a39ea2";
static const char urg_border[] = "#a39ea2";

static const char *colors[][3]      = {
    /*               fg           bg         border                         */
    [SchemeNorm] = { norm_fg,     norm_bg,   norm_border }, // unfocused wins
    [SchemeSel]  = { sel_fg,      sel_bg,    sel_border },  // the focused win
    [SchemeUrg] =  { urg_fg,      urg_bg,    urg_border },
};
