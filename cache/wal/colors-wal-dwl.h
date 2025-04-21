/* Taken from https://github.com/djpohly/dwl/issues/466 */
#define COLOR(hex)    { ((hex >> 24) & 0xFF) / 255.0f, \
                        ((hex >> 16) & 0xFF) / 255.0f, \
                        ((hex >> 8) & 0xFF) / 255.0f, \
                        (hex & 0xFF) / 255.0f }

static const float rootcolor[]             = COLOR(0x45475aff);
static uint32_t colors[][3]                = {
	/*               fg          bg          border    */
	[SchemeNorm] = { 0xa6adc8ff, 0x45475aff, 0x585b70ff },
	[SchemeSel]  = { 0xa6adc8ff, 0xa6e3a1ff, 0xf38ba8ff },
	[SchemeUrg]  = { 0xa6adc8ff, 0xf38ba8ff, 0xa6e3a1ff },
};
