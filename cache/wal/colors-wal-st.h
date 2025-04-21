const char *colorname[] = {

  /* 8 normal colors */
  [0] = "#45475a", /* black   */
  [1] = "#f38ba8", /* red     */
  [2] = "#a6e3a1", /* green   */
  [3] = "#f9e2af", /* yellow  */
  [4] = "#89b4fa", /* blue    */
  [5] = "#f5c2e7", /* magenta */
  [6] = "#94e2d5", /* cyan    */
  [7] = "#bac2de", /* white   */

  /* 8 bright colors */
  [8]  = "#585b70",  /* black   */
  [9]  = "#f38ba8",  /* red     */
  [10] = "#a6e3a1", /* green   */
  [11] = "#f9e2af", /* yellow  */
  [12] = "#89b4fa", /* blue    */
  [13] = "#f5c2e7", /* magenta */
  [14] = "#94e2d5", /* cyan    */
  [15] = "#a6adc8", /* white   */

  /* special colors */
  [256] = "#1e1e2e", /* background */
  [257] = "#cdd6f4", /* foreground */
  [258] = "#f5e0dc",     /* cursor */
};

/* Default colors (colorname index)
 * foreground, background, cursor */
 unsigned int defaultbg = 0;
 unsigned int defaultfg = 257;
 unsigned int defaultcs = 258;
 unsigned int defaultrcs= 258;
