const char *colorname[] = {

  /* 8 normal colors */
  [0] = "#15161e", /* black   */
  [1] = "#f7768e", /* red     */
  [2] = "#9ece6a", /* green   */
  [3] = "#e0af68", /* yellow  */
  [4] = "#7aa2f7", /* blue    */
  [5] = "#bb9af7", /* magenta */
  [6] = "#7dcfff", /* cyan    */
  [7] = "#a9b1d6", /* white   */

  /* 8 bright colors */
  [8]  = "#414868",  /* black   */
  [9]  = "#ff899d",  /* red     */
  [10] = "#9fe044", /* green   */
  [11] = "#faba4a", /* yellow  */
  [12] = "#8db0ff", /* blue    */
  [13] = "#c7a9ff", /* magenta */
  [14] = "#a4daff", /* cyan    */
  [15] = "#c0caf5", /* white   */

  /* special colors */
  [256] = "#1a1b26", /* background */
  [257] = "#c0caf5", /* foreground */
  [258] = "#c0caf5",     /* cursor */
};

/* Default colors (colorname index)
 * foreground, background, cursor */
 unsigned int defaultbg = 0;
 unsigned int defaultfg = 257;
 unsigned int defaultcs = 258;
 unsigned int defaultrcs= 258;
