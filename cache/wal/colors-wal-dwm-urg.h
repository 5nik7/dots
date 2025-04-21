static const char norm_fg[] = "#a6adc8";
static const char norm_bg[] = "#45475a";
static const char norm_border[] = "#585b70";

static const char sel_fg[] = "#a6adc8";
static const char sel_bg[] = "#a6e3a1";
static const char sel_border[] = "#a6adc8";

static const char urg_fg[] = "#a6adc8";
static const char urg_bg[] = "#f38ba8";
static const char urg_border[] = "#f38ba8";

static const char *colors[][3]      = {
    /*               fg           bg         border                         */
    [SchemeNorm] = { norm_fg,     norm_bg,   norm_border }, // unfocused wins
    [SchemeSel]  = { sel_fg,      sel_bg,    sel_border },  // the focused win
    [SchemeUrg] =  { urg_fg,      urg_bg,    urg_border },
};
