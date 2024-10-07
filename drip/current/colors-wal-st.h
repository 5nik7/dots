const char *colorname[] = {

  /* 8 normal colors */
  [0] = "#181e21", /* black   */
  [1] = "#a39ea2", /* red     */
  [2] = "#7999aa", /* green   */
  [3] = "#aa8586", /* yellow  */
  [4] = "#497baa", /* blue    */
  [5] = "#8a86a9", /* magenta */
  [6] = "#5f84aa", /* cyan    */
  [7] = "#c5c6c7", /* white   */

  /* 8 bright colors */
  [8]  = "#2c383e",  /* black   */
  [9]  = "#e8b8df",  /* red     */
  [10] = "#8accef", /* green   */
  [11] = "#f0999b", /* yellow  */
  [12] = "#4fa0ec", /* blue    */
  [13] = "#a49aef", /* magenta */
  [14] = "#6aabee", /* cyan    */
  [15] = "#fdffff", /* white   */

  /* special colors */
  [256] = "#181e21", /* background */
  [257] = "#fdffff", /* foreground */
  [258] = "#fdffff",     /* cursor */
};

/* Default colors (colorname index)
 * foreground, background, cursor */
 unsigned int defaultbg = 0;
 unsigned int defaultfg = 257;
 unsigned int defaultcs = 258;
 unsigned int defaultrcs= 258;
