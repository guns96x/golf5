"""Engine and vehicle formulas in SI units. Every function states its units in the name or docstring.

Sources for the formulas (definitions, not tuning folklore):
  - 4-stroke event rate, BMEP, P = T*omega: Heywood, Internal Combustion Engine Fundamentals, ch. 2
  - lambda / AFR definitions: Heywood ch. 3; SAE J1829 (stoichiometric AFR)
  - road load (inertia, rolling, aero, grade): standard longitudinal vehicle dynamics
    (e.g. Guzzella & Sciarretta, Vehicle Propulsion Systems, ch. 2)
"""
import math

G = 9.80665  # m/s^2, standard gravity (CGPM)
R_AIR = 287.05  # J/(kg K), specific gas constant of dry air


def rpm_to_rad_s(rpm):
    return rpm * 2.0 * math.pi / 60.0


def injections_per_s(rpm, n_cyl=4):
    """Main injection events per second for a 4-stroke engine: one per cylinder per 2 revolutions."""
    return n_cyl * rpm / 120.0


def fuel_flow_g_s(q_mg_stroke, rpm, n_cyl=4):
    return q_mg_stroke * 1e-3 * injections_per_s(rpm, n_cyl)


def fuel_flow_kg_h(q_mg_stroke, rpm, n_cyl=4):
    return fuel_flow_g_s(q_mg_stroke, rpm, n_cyl) * 3.6


def air_mg_stroke(maf_g_s, rpm, n_cyl=4):
    return maf_g_s * 1e3 / injections_per_s(rpm, n_cyl)


def lambda_from(air_mg, fuel_mg, afr_stoich):
    if fuel_mg <= 0 or air_mg <= 0:
        raise ValueError('lambda requires positive air and fuel mass')
    return air_mg / (fuel_mg * afr_stoich)


def q_max_for_lambda(air_mg, lam, afr_stoich):
    return air_mg / (lam * afr_stoich)


def power_w(torque_nm, rpm):
    return torque_nm * rpm_to_rad_s(rpm)


def w_to_ps(p_w):
    return p_w / 735.49875  # DIN 66036 metric horsepower


def w_to_hp(p_w):
    return p_w / 745.69987  # mechanical horsepower (550 ft*lbf/s)


def bmep_bar(torque_nm, displacement_m3):
    """4-stroke: BMEP = 4*pi*T / Vd."""
    return 4.0 * math.pi * torque_nm / displacement_m3 / 1e5


def torque_from_fuel_nm(q_mg_stroke, lhv_j_kg, eta_brake, n_cyl=4):
    """Brake torque from fuel energy: P = m_dot_f * LHV * eta, T = P / omega.
    Per 4-stroke cycle (4*pi rad): T = n_cyl * q * LHV * eta / (4*pi). rpm cancels."""
    return n_cyl * q_mg_stroke * 1e-6 * lhv_j_kg * eta_brake / (4.0 * math.pi)


def q_from_torque_mg(torque_nm, lhv_j_kg, eta_brake, n_cyl=4):
    return torque_nm * 4.0 * math.pi / (n_cyl * lhv_j_kg * eta_brake) * 1e6


def injection_ms(duration_deg_ca, rpm):
    """Crank angle to time: the crankshaft turns 6*rpm degrees per second."""
    return 1000.0 * duration_deg_ca / (6.0 * rpm)


def air_density(p_pa, t_k):
    return p_pa / (R_AIR * t_k)


def road_load_engine_torque_nm(rpm, drpm_dt, v_per_rpm, p):
    """Engine (flywheel) torque needed to produce the observed acceleration in a fixed gear.

    v = v_per_rpm * rpm  [m/s],   a = v_per_rpm * drpm/dt
    T_e = I_e * alpha_e + [ (m + I_w/r^2) * a + Crr*m*g*cos(th) + 0.5*rho*CdA*v^2 + m*g*sin(th) ] * v / (eta * omega_e)
    Engine rotating inertia acts before the driveline, so it is not divided by driveline efficiency.
    p: dict with mass_kg, inertia_engine_kgm2, inertia_wheels_kgm2, wheel_radius_m, crr, rho_air, cda_m2,
       grade_rad, eta_driveline.
    """
    v = v_per_rpm * rpm
    a = v_per_rpm * drpm_dt
    omega = rpm_to_rad_s(rpm)
    alpha = rpm_to_rad_s(drpm_dt)
    m = p['mass_kg']
    th = p['grade_rad']
    f_inertia = (m + p['inertia_wheels_kgm2'] / p['wheel_radius_m'] ** 2) * a
    f_roll = p['crr'] * m * G * math.cos(th)
    f_aero = 0.5 * p['rho_air'] * p['cda_m2'] * v * v
    f_grade = m * G * math.sin(th)
    return p['inertia_engine_kgm2'] * alpha + (f_inertia + f_roll + f_aero + f_grade) * v / (p['eta_driveline'] * omega)
