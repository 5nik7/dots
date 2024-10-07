const char *colorname[] = {

  /* 8 normal colors */
  [0] = "#142444", /* black   */
  [1] = "#FF5673", /* red     */
  [2] = "#00FFCC", /* green   */
  [3] = "#FFAA82", /* yellow  */
  [4] = "#3D81FF", /* blue    */
  [5] = "#A798F0", /* magenta */
  [6] = "#00E5FF", /* cyan    */
  [7] = "#D3EEFA", /* white   */

  /* 8 bright colors */
  [8]  = "#334775",  /* black   */
  [9]  = "#FF859B",  /* red     */
  [10] = "#8FF8B5", /* green   */
  [11] = "#FFC990", /* yellow  */
  [12] = "#508FF8", /* blue    */
  [13] = "#ABAFFF", /* magenta */
  [14] = "#30F1EA", /* cyan    */
  [15] = "#E4F0FF", /* white   */

  /* special colors */
  [256] = "#142444", /* background */
  [257] = "#E4F0FF", /* foreground */
  [258] = "#D3EEFA",     /* cursor */
};

/* Default colors (colorname index)
 * foreground, background, cursor */
 unsigned int defaultbg = 0;
 unsigned int defaultfg = 257;
 unsigned int defaultcs = 258;
 unsigned int defaultrcs= 258;
