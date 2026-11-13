# Variable Table

| Symbol | Name | Unit | Source | Registry ID |
|---|---|---|---|---|
| $\eta_{ref}$ | Reference electrical efficiency | — | Datasheet / literature | `pvt_el.eta_ref` |
| $eta$ | Temperature coefficient of electrical efficiency | K$^{-1}$ | Datasheet / literature | `pvt_el.beta` |
| $T_c$ | Cell temperature | K | Derived from thermal balance | `pvt_el.T_ref` |
| $T_{ref}$ | Reference temperature | K | Datasheet | `pvt_el.T_ref` |
| $\phi_{soil}$ | Soiling factor | — | External table | `soiling_factor` |
| $G_{eff}$ | Effective irradiance | W/m$^2$ | Weather + transposition | `weather.G_poa` |
| $A$ | Collector area | m$^2$ | Parameter registry | `pvt_th.collector_area` |
| $F_R$ | Heat-removal factor | — | Collector model | `pvt_th.F_R` |
| $U_L$ | Collector heat-loss coefficient | W/m$^2$/K | Parameter registry | `pvt_th.U_L` |
| $T_{f,in}$ | Inlet fluid temperature | K | Input / derived | `loop.T_inlet` |
| $T_{f,out}$ | Outlet fluid temperature | K | Solver output | `pvt.T_f_out` |
| $\dot{m}$ | Mass flow rate | kg/s | Loop parameter | `loop.mass_flow` |
| $c_{p,f}$ | Fluid specific heat | J/kg/K | Parameter registry | `loop.fluid_cp` |
| $Q_u$ | Useful thermal output | W | Solver output | `pvt.Q_u` |
| $ho$ | Water density | kg/m$^3$ | Material property | `tank.rho` |
| $V_i$ | Node volume | m$^3$ | Tank discretization | `tank.node_volume` |
| $T_i$ | Node temperature | K | tank state | `tank.node_temp` |
| $m_{feed}$ | Feed flow rate | kg/s | Treatment Table | `water.feed_flow` |
| $m_{prod}$ | Product flow rate | kg/s | Treatment Table | `water.product_flow` |
| $m_{rej}$ | Reject flow rate | kg/s | Treatment Table | `water.reject_flow` |
| $R$ | Recovery fraction | — | Water balance | `water.recovery` |
