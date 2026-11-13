# Mathematical Equations

## PVT subsystem

### EQ-PVT-01: Electrical output
$$P_{el} = \eta_{ref}\left[1 - \beta (T_c - T_{ref})\right]\phi_{soil}G_{eff}A f_{irr}f_{MPP}$$

### EQ-PVT-02: Useful thermal output
$$Q_u = A F_R \left[S - U_L (T_{f,in} - T_a)\right], \qquad S = \tau_{\alpha} G_{eff} - \frac{P_{el}}{A}$$

### EQ-PVT-03: Cell-to-fluid thermal relation
$$T_c = T_{f,m} + R_{cf} q_{cf}, \qquad T_{f,m} = \frac{T_{f,in} + T_{f,out}}{2}$$

### EQ-PVT-04: Outlet temperature
$$T_{f,out} = T_{f,in} + \frac{Q_u}{\dot{m} c_{p,f}}$$

## Loop subsystem

### EQ-LP-01: Differential controller logic
$$\text{Pump ON if } T_{coll} - T_{tank} > \Delta T_{on}; \quad \text{Pump OFF if } T_{coll} - T_{tank} < \Delta T_{off}$$

### EQ-LP-03: Pipe heat loss
$$Q_{pipe} = UA_{pipe}(T_{f,mean} - T_{amb,pipe})$$

## Tank subsystem

### EQ-TNK-01: Node energy balance
$$\rho c_p V_i \frac{dT_i}{dt} = Q_{charge,i} + Q_{adv,i} + Q_{cond,i} - Q_{loss,i} + Q_{aux,i}$$

### EQ-TNK-03: Axial conduction
$$Q_{cond,i} = \frac{k_{eff} A_x}{\Delta z}(T_{i+1} - 2T_i + T_{i-1})$$

### EQ-TNK-04: Standby loss
$$Q_{loss,i} = UA_i (T_i - T_{amb})$$

### EQ-TNK-05: Inversion mixing
$$T_{mix} = \frac{\sum_i \rho c_p V_i T_i}{\sum_i \rho c_p V_i}$$

### EQ-TNK-06: Coil/exchanger charging
$$Q_{charge} = \epsilon C_{min}(T_{loop,in} - T_{node})$$

### EQ-TNK-07: Backup heater control
$$Q_{aux} = \begin{cases} Q_{aux,max}, & T_{node} < T_{set} \\ 0, & \text{otherwise} \end{cases}$$

### EQ-TNK-08: Delivered temperature and unmet demand
$$T_{delivered} = \min\left(T_{tank}, T_{requested}\right), \quad D_{unmet} = \max(0, T_{demand} - T_{delivered})$$

## Water-treatment subsystem

### EQ-WTR-01: Feed-product-reject balance
$$m_{feed} = m_{prod} + m_{rej}$$

### EQ-WTR-02: Product recovery and rejection
$$R = \frac{V_{prod}}{V_{feed}}, \qquad R_k = 1 - \frac{c_{prod}}{c_{feed}}$$

### EQ-WTR-03: Hydraulic power
$$P_{hyd} = Q_{feed}\frac{\Delta p}{\eta_{pump}}$$

### EQ-WTR-04: Specific energy consumption
$$E_{spec} = \frac{E_{electric}}{V_{prod}}$$

### EQ-WTR-05: Membrane flux
$$J = K_{mem}(\Delta P - \Delta \pi)$$

### EQ-WTR-06: Consumable loading
$$N_{replace} = \left\lceil \frac{\text{loading}_{used}}{\text{loading}_{limit}} \right\rceil$$

### EQ-WTR-07: UV dose
$$D_{UV} = I_{UV} \cdot t_{exposure}$$

### EQ-WTR-08: Remineralization
$$C_{final} = C_{treated} + C_{added}$$

## Storage quality and electrical/economic subsystem

### EQ-SQ-01: Storage disinfectant decay
$$V_s \frac{dC}{dt} = Q_{in}C_{in} - Q_{out}C - k(T)V_s C$$

### EQ-ELC-01: Electrical balance
$$E_{el,total} = E_{PVT} + E_{grid} - E_{dump}$$

### EQ-ECO-01: Levelized cost proxy
$$LC = \frac{\text{Annualized capital and operating cost}}{\text{Annual product water volume}}$$
