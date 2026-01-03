/* Taken from https://github.com/djpohly/dwl/issues/466 */
#define COLOR(hex)    { ((hex >> 24) & 0xFF) / 255.0f, \
                        ((hex >> 16) & 0xFF) / 255.0f, \
                        ((hex >> 8) & 0xFF) / 255.0f, \
                        (hex & 0xFF) / 255.0f }

static const float rootcolor[]             = COLOR(0x15161eff);
static uint32_t colors[][3]                = {
	/*               fg          bg          border    */
	[SchemeNorm] = { 0xc0caf5ff, 0x15161eff, 0x414868ff },
	[SchemeSel]  = { 0xc0caf5ff, 0x9ece6aff, 0xf7768eff },
	[SchemeUrg]  = { 0xc0caf5ff, 0xf7768eff, 0x9ece6aff },
};
