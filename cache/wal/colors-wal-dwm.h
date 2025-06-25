static const char norm_fg[] = "#A6ADC8";
static const char norm_bg[] = "#45475A";
static const char norm_border[] = "#585B70";

static const char sel_fg[] = "#A6ADC8";
static const char sel_bg[] = "#A6E3A1";
static const char sel_border[] = "#A6ADC8";

static const char urg_fg[] = "#A6ADC8";
static const char urg_bg[] = "#F38BA8";
static const char urg_border[] = "#F38BA8";

static const char *colors[][3]      = {
    /*               fg           bg         border                         */
    [SchemeNorm] = { norm_fg,     norm_bg,   norm_border }, // unfocused wins
    [SchemeSel]  = { sel_fg,      sel_bg,    sel_border },  // the focused win
    [SchemeUrg] =  { urg_fg,      urg_bg,    urg_border },
};
