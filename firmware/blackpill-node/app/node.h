#ifndef NODE_H
#define NODE_H

/* Application entry points, called from the CubeIDE-generated main().
 *   node_setup(): after MX_*_Init(), pass &hadc1, &htim2, &huart1.
 *   node_loop():  call repeatedly from the main while(1).
 * Keeping the app here means the generated main.c only needs two USER CODE
 * lines, so regenerating from the .ioc never clobbers application logic. */
void node_setup(void *hadc1, void *htim2, void *huart1);
void node_loop(void);

#endif /* NODE_H */
