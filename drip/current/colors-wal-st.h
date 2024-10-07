const char *colorname[] = {

  /* 8 normal colors */
  [0] = "#142444", /* black   */
  [1] = "#907277", /* red     */
  [2] = "#4C5370", /* green   */
  [3] = "#A5897F", /* yellow  */
  [4] = "#375785", /* blue    */
  [5] = "#635E70", /* magenta */
  [6] = "#5B6789", /* cyan    */
  [7] = "#d3eefa", /* white   */

  /* 8 bright colors */
  [8]  = "#334775",  /* black   */
  [9]  = "#cb838f",  /* red     */
  [10] = "#56649d", /* green   */
  [11] = "#e9a992", /* yellow  */
  [12] = "#3b6eb9", /* blue    */
  [13] = "#7a6c9e", /* magenta */
  [14] = "#677ec0", /* cyan    */
  [15] = "#e4f0ff", /* white   */

  /* special colors */
  [256] = "#142444", /* background */
  [257] = "#e4f0ff", /* foreground */
  [258] = "#e4f0ff",     /* cursor */
};

/* Default colors (colorname index)
 * foreground, background, cursor */
 unsigned int defaultbg = 0;
 unsigned int defaultfg = 257;
 unsigned int defaultcs = 258;
 unsigned int defaultrcs= 258;
