const char *colorname[] = {

  /* 8 normal colors */
  [0] = "#45475A", /* black   */
  [1] = "#F38BA8", /* red     */
  [2] = "#A6E3A1", /* green   */
  [3] = "#F9E2AF", /* yellow  */
  [4] = "#89B4FA", /* blue    */
  [5] = "#F5C2E7", /* magenta */
  [6] = "#94E2D5", /* cyan    */
  [7] = "#BAC2DE", /* white   */

  /* 8 bright colors */
  [8]  = "#585B70",  /* black   */
  [9]  = "#F38BA8",  /* red     */
  [10] = "#A6E3A1", /* green   */
  [11] = "#F9E2AF", /* yellow  */
  [12] = "#89B4FA", /* blue    */
  [13] = "#F5C2E7", /* magenta */
  [14] = "#94E2D5", /* cyan    */
  [15] = "#A6ADC8", /* white   */

  /* special colors */
  [256] = "#1E1E2E", /* background */
  [257] = "#CDD6F4", /* foreground */
  [258] = "#F5E0DC",     /* cursor */
};

/* Default colors (colorname index)
 * foreground, background, cursor */
 unsigned int defaultbg = 0;
 unsigned int defaultfg = 257;
 unsigned int defaultcs = 258;
 unsigned int defaultrcs= 258;
