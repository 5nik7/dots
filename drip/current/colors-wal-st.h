const char *colorname[] = {

  /* 8 normal colors */
  [0] = "#181e21", /* black   */
  [1] = "#7b99aa", /* red     */
  [2] = "#497baa", /* green   */
  [3] = "#5f85aa", /* yellow  */
  [4] = "#8983aa", /* blue    */
  [5] = "#a39ea2", /* magenta */
  [6] = "#aa8486", /* cyan    */
  [7] = "#c5c6c7", /* white   */

  /* 8 bright colors */
  [8]  = "#515658",  /* black   */
  [9]  = "#7b99aa",  /* red     */
  [10] = "#497baa", /* green   */
  [11] = "#5f85aa", /* yellow  */
  [12] = "#8983aa", /* blue    */
  [13] = "#a39ea2", /* magenta */
  [14] = "#aa8486", /* cyan    */
  [15] = "#c5c6c7", /* white   */

  /* special colors */
  [256] = "#181e21", /* background */
  [257] = "#c5c6c7", /* foreground */
  [258] = "#c5c6c7",     /* cursor */
};

/* Default colors (colorname index)
 * foreground, background, cursor */
 unsigned int defaultbg = 0;
 unsigned int defaultfg = 257;
 unsigned int defaultcs = 258;
 unsigned int defaultrcs= 258;
