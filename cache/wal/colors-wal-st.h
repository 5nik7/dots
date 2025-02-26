const char *colorname[] = {

  /* 8 normal colors */
  [0] = "#2E3C5B", /* black   */
  [1] = "#EB6F92", /* red     */
  [2] = "#00FFCC", /* green   */
  [3] = "#FFB78D", /* yellow  */
  [4] = "#477EFF", /* blue    */
  [5] = "#9896FF", /* magenta */
  [6] = "#00FFFB", /* cyan    */
  [7] = "#d6e9ff", /* white   */

  /* 8 bright colors */
  [8]  = "#374B72",  /* black   */
  [9]  = "#EB6F92",  /* red     */
  [10] = "#8FF8B5", /* green   */
  [11] = "#F2C996", /* yellow  */
  [12] = "#5792FF", /* blue    */
  [13] = "#A7A6FF", /* magenta */
  [14] = "#30F1EA", /* cyan    */
  [15] = "#d6e9ff", /* white   */

  /* special colors */
  [256] = "#151D38", /* background */
  [257] = "#d6e9ff", /* foreground */
  [258] = "#5500FF",     /* cursor */
};

/* Default colors (colorname index)
 * foreground, background, cursor */
 unsigned int defaultbg = 0;
 unsigned int defaultfg = 257;
 unsigned int defaultcs = 258;
 unsigned int defaultrcs= 258;
