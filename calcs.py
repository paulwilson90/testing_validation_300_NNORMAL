import json
import math
import pandas as pd

RED = '\033[31m'
REDEND = '\033[0m'



def get_uld(elevation, flap, weight):
    """Gets the ULD by interpolating and using index locations from the QRH
    It grabs the weight one tonne up and below and the elevation INDEX position one up and below.
    It then interpolates using the percentage of the remaining index location."""
    if flap == 0 or flap == 5 or flap == 10:
        flap = 35
    weight_tonnes = weight / 1000
    print(weight_tonnes)
    flap = str(int(flap))
    wt_up = str(math.ceil(float(weight_tonnes)))
    wt_down = str(math.floor(float(weight_tonnes)))
    with open('ulds_q300.json') as ulds:
        uld_ = json.load(ulds)
    elevation_up = math.ceil(elevation)
    elevation_down = math.floor(elevation)
    # interpolating with the upper weight of the two elevation figures
    wt_up_up_data = uld_[flap][wt_up][elevation_up]
    wt_up_dwn_data = uld_[flap][wt_up][elevation_down]
    uld_up_wt = round(wt_up_dwn_data + ((wt_up_up_data - wt_up_dwn_data) * (elevation - elevation_down)))
    # interpolating with the lower weight of the two elevation figures
    wt_dwn_up_data = uld_[flap][wt_down][elevation_up]
    wt_dwn_dwn_data = uld_[flap][wt_down][elevation_down]
    uld_dwn_wt = round(wt_dwn_dwn_data + ((wt_dwn_up_data - wt_dwn_dwn_data) * (elevation - elevation_down)))
    # interpolating for weight between the two elevation interpolated figures
    final_uld = round(uld_dwn_wt + (uld_up_wt - uld_dwn_wt) * (float(weight_tonnes) - int(wt_down)))

    return final_uld


def wind_correct_formulated(ULD, wind_comp, flap):
    """for every m above 530 ULD, take off 0.0025m (0.4 change over 160) on top of the base 3 for every knot head
    for every m above 530 ULD, add 0.01125m on top of the base 9.6 for every knot tail

    flap 35 (0.4 diff over 160) means take 0.0025m on top of 3 base for every knot of head  **** Same as F15 head *****
    flap 35 (0.8 diff over 160) means add 0.005 on top base 10 for any over 520 for tail

    NEED TO FIGURE THE PERCENT INCREASE FOR 20 TAIL, CURRENTLY SET AT THE Q400 RATE OF 1.6% PER KNOT OVER 10T"""
    flap = str(flap)
    if flap == "15":
        amount_above_base_ULD = ULD - 530
    else:
        amount_above_base_ULD = ULD - 520
    if wind_comp > 0:  # headwind
        factor_above_uld = amount_above_base_ULD * 0.0025
        wind_corr_ULD = round(ULD - (wind_comp * (3 + factor_above_uld)))
    else:  # tailwind (this differs between flap 15 and 35
        if flap == "15":
            factor_above_uld = amount_above_base_ULD * 0.01125
            wind_corr_ULD = ULD - round((wind_comp * (9.6 + factor_above_uld)))
        else:  # flap 35 tailwind
            factor_above_uld = amount_above_base_ULD * 0.005
            wind_corr_ULD = ULD - round((wind_comp * (10 + factor_above_uld)))
    """I dont know what the addit for tailwind over 10 is. I wasn't given an AOM which has the chart"""
    if wind_comp < -10:  # if the wind is more than 10 knot tail, add 1.6% for every knot over 10t
        if flap == "15":
            factor_above_uld = (amount_above_base_ULD / 100)
            ten_tail_ULD = ULD - round((-10 * (9.6 + factor_above_uld)))
            wind_corr_ULD = int(ten_tail_ULD * (1 + ((abs(wind_comp) - 10) * 1.6) / 100))
        else:
            factor_above_uld = (amount_above_base_ULD / 100)
            ten_tail_ULD = ULD - round((-10 * (10 + factor_above_uld)))
            wind_corr_ULD = int(ten_tail_ULD * (1 + ((abs(wind_comp) - 10) * 1.6) / 100))
    return int(wind_corr_ULD)


def slope_corrected(slope, wind_corrected_ld, flap):
    """If the slope is greater than 0, the slope is going uphill so the distance will be shorter
    IF the slope is less than 0 however, the slope is downhill and the distance increases."""
    flap = str(flap)
    if flap == "15":
        if slope < 0:  # if the slope is downhill
            slope_correct = wind_corrected_ld + (wind_corrected_ld * (abs(slope) * 0.1))
        else:  # if the slope is uphill
            slope_correct = wind_corrected_ld - (wind_corrected_ld * (abs(slope) * 0.07))

    else:  # flap 35
        if slope < 0:  # if the slope is downhill
            slope_correct = wind_corrected_ld + (wind_corrected_ld * (abs(slope) * 0.112))
        else:  # if the slope is uphill
            slope_correct = wind_corrected_ld - (wind_corrected_ld * (abs(slope) * 0.08))
    return int(slope_correct)


def get_v_speeds(weight, flap, vapp_addit, ice, ab_fctr):
    flap = str(flap)
    weight = str((math.ceil(weight / 500) * 500) / 1000)
    print(f"Using {weight}t as the weight to get VREF")
    # reading the excel file
    xl = pd.ExcelFile('300_MELCDL_MULTIPLIERS.xlsx')
    Q400 = pd.read_excel(xl, 'NON NORMAL')
    # getting the appropriate speed addit or VS, if none apply, the speed variable will return nan...
    for line in range(len(Q400)):
        all_rows = Q400.loc[line]
        if all_rows['Problem'] == ab_fctr:
            speed = all_rows['F' + flap + " Add"]
    # get the unaltered 1.3 VREF speed
    with open('ref_speeds.json') as file:
        f = json.load(file)
    vref = f[flap][weight]
    # if the QRH specifies a speed for approach for the specific failure, determine whether its a 1.4vs
    # or an additive to the 1.3 VS/VREF and apply. This will become the new VREF.
    if not pd.isnull(speed):
        print("There is a QRH prescribed landing speed", speed)
        if speed == 1.4:
            with open("one_point_four.json") as one_point_four:
                o_p_f = json.load(one_point_four)
                vref = o_p_f[flap][weight]
        else:
            vref = int(vref + speed)
    # apply the INCR REF speed applicable to flap setting
    vapp = int(vref) + vapp_addit
    if flap == "0":
        vref_ice = vref + 20
    elif flap == "5":
        vref_ice = vref + 15
    elif flap == "10":
        vref_ice = vref + 15
    elif flap == "15":
        vref_ice = vref + 10
    else:
        vref_ice = vref + 5
    # if the ice protection is ON, then VAPP will become VREF ICE
    if ice == "On":
        vapp = vref_ice
    print(vref, "VREF ADDIT", vapp_addit, "VAPP", vapp, "VREF ICE", vref_ice)
    return vapp, vref, vref_ice


def abnormal_factor(ab_fctr, corrected_for_slope, flap, ice):
    """Take in the abnormal factor from the excel sheet and pull its factor from the Multipliers excel sheet
    Return the landing distance required after applying the factor to the slope corrected distance. This is
    either the ice ON or OFF distance, not both....
    Return the multiplier used to get the distance.
    If N/A is listed in the MELCDL_MULTIPLIERS sheet for the current flap setting for the abnormal, a parameter
    can_land_in_this_config is returned as false and the remaining calculations won't be displayed in final sheet.
    For the classic ref speed on multipliers that don't exist in the QRH, We multiply the ice off factor by the
    normal ice protection on additive. That being 16% for flap 15 and 10% for flap 35.
    """
    print(ab_fctr, "Is the Abnormality")
    can_land_in_this_config = True
    flap = str(flap)
    xl = pd.ExcelFile('300_MELCDL_MULTIPLIERS.xlsx')
    Q400 = pd.read_excel(xl, 'NON NORMAL')
    for line in range(len(Q400)):
        all_rows = Q400.loc[line]
        if all_rows['Problem'] == ab_fctr:
            multiplier = all_rows['F' + flap + " " + ice]
    if ab_fctr == "EXTENDED DOOR OPEN" or ab_fctr == "EXTENDED DOOR CLOSED":  # due to it being WAT and MLDW issue only
        multiplier = 1
    if pd.isnull(multiplier):  # means the multiplier is N/A and not for landing in this config
        multiplier = 1
        can_land_in_this_config = False

    distance = corrected_for_slope * multiplier

    print("Abnormal Multiplier with the ice protection", ice, "is", multiplier, "giving a new distance required of",
          distance)
    return int(distance), multiplier, can_land_in_this_config


def vapp_corrections(abnormal_dist, vref_addit, wet_dry):
    """Apply Operational Correction
        Factor
        1.40 (Dry VREF+10) Every knot is 1.04
        1.40 (Wet VREF)
        1.60 (Wet VREF+10) Every knot is 1.02
        """

    if wet_dry == "Wet":
        percent_increase = 1.4 + (vref_addit * 0.02)
    else:
        percent_increase = 1 + (vref_addit * 0.04)

    abnormal_vapp_adjusted_ld = abnormal_dist * percent_increase

    print(f"It is {wet_dry} VREF + {vref_addit} so the multiplier is {percent_increase}."
          f"This gives us {int(abnormal_vapp_adjusted_ld)} as the distance")

    return int(abnormal_vapp_adjusted_ld)


def company_addit_dry_wet(vapp_corrected_ld):
    """Applying 15% addition to the vapp corrected landing distance"""
    operational_fact_adjusted_ld = vapp_corrected_ld * 1.15
    return int(operational_fact_adjusted_ld)


def get_torque_limits(temp, pressure_alt, vapp, bleeds):
    if bleeds == "On":
        temp = temp + 7
    if temp < 14:
        temp = 14
    if temp > 48:
        temp = 48
    if pressure_alt > 4000:
        pressure_alt = 4000
    if pressure_alt < 0:
        pressure_alt = 0
    temp = str(temp)
    pressure_alt = pressure_alt / 500
    with open('takeoff_torques.json') as file:
        torque = json.load(file)

    elev_up = math.ceil(pressure_alt)
    elev_down = math.floor(pressure_alt)
    temp_up = str(math.ceil(int(temp) / 2) * 2)
    temp_down = str(math.floor(int(temp) / 2) * 2)
    power = ["NTOP", "MTOP"]
    for lst in range(len(power)):
        # interpolating with the upper temp of the two elevation figures
        temp_up_up_data = torque[temp_up][elev_up][lst]
        temp_up_dwn_data = torque[temp_up][elev_down][lst]
        temp_up_wt = temp_up_dwn_data + ((temp_up_up_data - temp_up_dwn_data) * (pressure_alt - elev_down))
        # interpolating with the lower temp of the two elevation figures
        temp_dwn_up_data = torque[temp_down][elev_up][lst]
        temp_dwn_dwn_data = torque[temp_down][elev_down][lst]
        temp_dwn_wt = temp_dwn_dwn_data + ((temp_dwn_up_data - temp_dwn_dwn_data) * (pressure_alt - elev_down))

        torque_limit = (temp_up_wt + temp_dwn_wt) / 2

        power[lst] = torque_limit
    ntop = power[0]
    mtop = power[1]
    if ntop > 90:
        ntop = 90
    if mtop > 100:
        mtop = 100

    if vapp > 100:
        amount_over = vapp - 100
        for_every_two = amount_over / 2
        add_point_one = for_every_two * 0.1
        ntop = ntop + add_point_one
        mtop = mtop + add_point_one

    else:
        amount_under = 100 - vapp
        for_every_three = amount_under / 3
        subtract_point_one = for_every_three * 0.1
        ntop = ntop - subtract_point_one
        mtop = mtop - subtract_point_one

    if ntop > 90:
        ntop = 90
    if mtop > 100:
        mtop = 100

    return round(ntop, 2), round(mtop, 2)


def get_oei_climb(temp, elev, flap, weight):
    """scale is 0.002 units per dashed line
    Q300"""
    elev = elev * 500
    weight = weight / 1000
    elevation_envelope = -0.10
    if temp <= 42:
        temp_diff = 42 - temp
        elevation_envelope = temp_diff * 230
    print(elevation_envelope, "Elevation envelope")
    if flap == "10":
        ref_weight = 14
        weight_change = 0.009
        if elev > elevation_envelope:
            print("Bottom scale")
            temp_change = 0.0014
            elev_change = 0.007
            base = 0.1337

        else:
            print("Top scale")
            temp_change = 0.00027
            elev_change = 0.0025
            base = 0.087
    else:  # flap 15 missed
        ref_weight = 14
        weight_change = 0.009
        if elev > elevation_envelope:
            print("Bottom scale")
            temp_change = 0.0013
            elev_change = 0.0069
            base = 0.1218
        else:
            print("Top scale")
            temp_change = 0.00026
            elev_change = 0.0025
            base = 0.079

    temp_elev_units = base - (temp * temp_change) - ((elev / 1000) * elev_change)
    print(temp_elev_units, "temp elev")

    variance_from_12t = weight - ref_weight
    weight_units = variance_from_12t * weight_change
    initial_units = temp_elev_units - weight_units
    print(initial_units)

    return round(initial_units * 100, 2)


def get_wat_limit(temp, flap, ice_protection, bleed, pressure_alt, test_case):
    """Take in the temp, flap, bleed position and pressure altitude as parameters
    and return the max landing weight.
    Also trying to keep indexes in range as some temperatures and pressure altitudes are off charts.
    The minimum pressure alt for the chart is 0 and the max is 4000.
    The minimum temperature is 0 and the max is 48, even after the 11 degree addit"""
    off_chart_limits = False
    rpm = "MAX"
    flap = str(int(flap))
    MLDW = 19051

    if pressure_alt < 0:
        pressure_alt = 0
        off_chart_limits = True
    else:
        if pressure_alt > 4000:
            pressure_alt = 4000 / 500
            off_chart_limits = True
        else:
            pressure_alt = pressure_alt / 500
    if bleed == "On":
        temp = int(temp) + 7

    if temp > 48:
        temp = str(48)
        off_chart_limits = True
        if pressure_alt > 2:
            pressure_alt = 2
    else:
        if temp < 0:
            temp = str(0)
            off_chart_limits = True
        else:
            temp = str(temp)

    with open(f'wat_f15.json') as r:
        wat = json.load(r)
    elev_up = math.ceil(pressure_alt)
    elev_down = math.floor(pressure_alt)
    temp_up = str(math.ceil(int(temp) / 2) * 2)
    temp_down = str(math.floor(int(temp) / 2) * 2)

    # interpolating with the upper temp of the two elevation figures
    try:
        temp_up_up_data = wat[rpm][temp_up][elev_up]
    except Exception as err:
        print(RED + "ERROR" + REDEND, err, "TEST CASE", test_case)

    temp_up_dwn_data = wat[rpm][temp_up][elev_down]
    temp_up_wt = round(temp_up_dwn_data + ((temp_up_up_data - temp_up_dwn_data) * (pressure_alt - elev_down)))
    # interpolating with the lower temp of the two elevation figures
    temp_dwn_up_data = wat[rpm][temp_down][elev_up]
    temp_dwn_dwn_data = wat[rpm][temp_down][elev_down]
    temp_dwn_wt = round(temp_dwn_dwn_data + ((temp_dwn_up_data - temp_dwn_dwn_data) * (pressure_alt - elev_down)))

    wat_limit = int((temp_up_wt + temp_dwn_wt) / 2)
    if ice_protection == "On":
        wat_limit = wat_limit - 180

    if flap == "35":  # Assumption is that aircraft will continue to land at flap 35
        return 19051, MLDW, off_chart_limits
    if flap == "10" or flap == "5" or flap == "0":  # Should be able to climb with no WAT limit at these flap settings
        return 19051, MLDW, off_chart_limits

    return wat_limit, MLDW, off_chart_limits


def max_landing_wt_lda(lda, operation_fact_corrected_ld, flap, weight, unfact_uld):
    """Find the ratio between the landing distance required and the unfactored ULD which returns a multiplier ratio
    Divide the landing distance available by the ratio to find the relative unfactored ULD
    Get the difference between the maximum (LDA based) ULD and the current ULD and divide by 23.8 for flap 15 or
    22.6 for flap 35 and multiply by 1000 (This is ULD difference for every tonne) this will give the weight
    to add onto the current landing weight which will give the max field landing weight.
    This is correct for the Q300"""
    flap = str(flap)
    if flap == "15":
        ratio = operation_fact_corrected_ld / unfact_uld
        max_unfact_uld = lda / ratio
        diff_between_ulds = max_unfact_uld - unfact_uld
        final = ((diff_between_ulds / 23.8) * 1000) + weight
    else:
        ratio = operation_fact_corrected_ld / unfact_uld
        max_unfact_uld = lda / ratio
        diff_between_ulds = max_unfact_uld - unfact_uld
        final = ((diff_between_ulds / 22.6) * 1000) + weight
    return int(final)


def max_brake_energy_wt(flap, temp, elev, weight, head_tail):
    """ example using flap 15...
    for every X degrees C, increase by Y units (0.032 per degree). starting at 0 degrees base of 8 at sea
    level.
    add 0.4 for every 1000' elevation.
    starting from 14t. every 1t = 1.8 units
    + 4.5 for every 10kt tail
    - 1.2 for every 10 kt tail """
    weight = int(weight) / 1000
    flap = str(flap)
    temp = int(temp)
    elev = int(elev * 500)
    head_tail = int(head_tail)
    print(flap, temp, elev, weight, head_tail)
    max_brake_limit = 22.54
    if flap == "15":
        temp_change = 0.032
        base = 8
        elev_change = 0.4
        ref_weight = 14
        weight_change = 1.8
        tail_change = 0.45
        head_change = 0.12
    else:
        temp_change = 0.025
        base = 6.3
        elev_change = 0.25
        ref_weight = 14
        weight_change = 1.55
        tail_change = 0.3
        head_change = 0.1

    temp_elev_units = base + (temp * temp_change) + ((elev / 1000) * elev_change)
    variance_from_14t = weight - ref_weight
    weight_units = variance_from_14t * weight_change
    initial_units = temp_elev_units + weight_units
    if head_tail < 0:
        final_brake_energy = initial_units + (abs(head_tail) * tail_change)
    else:
        final_brake_energy = initial_units - (abs(head_tail) * head_change)
    print(final_brake_energy, "is the brake energy")
    difference_between_current_and_max = max_brake_limit - final_brake_energy
    max_weight = ref_weight + ((weight_units + difference_between_current_and_max) / weight_change)
    print(int(max_weight * 1000), "Is the max brake energy weight for given conditions")
    return int(max_weight * 1000)


def final_max_weight(max_wat, max_field, max_brake_nrg_weight, MLDW, off_chart):
    """Find and return the lowest weight out of all provided. Also add * to any code where the wat weight
    used a parameter that was off chart."""
    weights = [max_wat, max_field, max_brake_nrg_weight, MLDW]
    # Find the minimum weight
    min_weight = min(weights)

    # Assign the corresponding code
    if min_weight == max_wat:
        code_max = "(c)"
    elif min_weight == max_field:
        code_max = "(f)"
    elif min_weight == max_brake_nrg_weight:
        code_max = "(b)"
    else:
        code_max = "(s)"

    # Add * if off_chart is True
    if off_chart:
        code_max += "*"

    if off_chart:
        max_weight = str(min_weight) + code_max + "^"
    else:
        max_weight = str(min_weight) + code_max
    return max_weight
