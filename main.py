import pandas as pd
import re
from math import radians, sin
from calcs import get_uld, company_addit_dry_wet, get_wat_limit, final_max_weight, get_v_speeds
from calcs import slope_corrected, vapp_corrections, wind_correct_formulated, max_landing_wt_lda
from calcs import abnormal_factor, max_brake_energy_wt, get_torque_limits, get_oei_climb

"""To auto space the columns in Excel: right click worksheet, view code, dropdown to worksheet and type:"""
""" Cells.EntireColumn.AutoFit """

"""Made change to WAT limit where if flap anything below 15, return max weights as climb should be unrestricted"""

xls = pd.ExcelFile('Q300 Landing Non Normal Version Control Test Cases.xlsx')
Q400 = pd.read_excel(xls, 'Q300 Non Normal')

all_excel_data = {"Test Case Number": [], "Airport Code": [], "Destination": [], "Runway": [],
                  "Elevation": [], "LDA": [], "Slope": [], "Grooved/Ungrooved": [], "Wind Direction": [],
                  "Wind Speed": [], '"HW (+) / TW (-) Comp"': [], "Temp": [], "QNH": [], "Dry/Wet": [],
                  "Weight": [], "VREF Additive": [], "Flaps": [], "Bleeds": [],
                  "Ice protection": [], "Pressure Altitude": [], "Abnormality": [], "Factor Applied": [],
                  "MLDW": [], "NTOP": [], "MTOP": [], "Unfactored ULD": [], "ULD": [],
                  "LDR": [], "Vapp": [], "VREF": [], "VREF ICE": [], "OEI Gradient": []}


def all_data(all_row_data):
    """Store all the headings from the Excel file
    :arg all_row_data which is each heading item from each row"""
    test_case_number = all_row_data['Test Case Number']
    airport_code = all_row_data['Airport Code']
    destination = all_row_data['Destination']
    runway = all_row_data['Runway']
    elevation = all_row_data['Elevation']
    lda = all_row_data['LDA']
    slope = all_row_data['Slope']
    grooved_ungrooved = all_row_data['Grooved/Ungrooved']
    wind_direction = all_row_data['Wind Direction']
    wind_speed = all_row_data['Wind Speed']
    head_tail = all_row_data['HW (+) / \nTW (-) Comp']
    temp = int(all_row_data['Temp'])
    qnh = all_row_data['QNH']
    wet_dry = all_row_data['Dry/Wet']
    weight = all_row_data['Weight']
    vref_addit = all_row_data['VREF Additive']
    flap = all_row_data['Flaps']
    bleeds = all_row_data['Bleeds']
    ice = all_row_data['Ice protection']

    ab_fctr = all_row_data['Non Normal'].upper()

    pressure_altitude = (elevation + ((1013 - qnh) * 30))
    elevation = elevation / 500

    str_rwy = str(runway)
    check_ = re.search("\d\d", str_rwy)
    if not check_:
        str_rwy = "0" + str_rwy
    cross_runway = int(re.search("\d\d", str_rwy).group()) * 10
    radian = radians(cross_runway - wind_direction)
    crosswind = abs(round(sin(radian) * wind_speed))

    final_uld = get_uld(elevation, flap, weight)
    print("Flap", flap, "Weight", weight, "LDA", lda, "Bleed", bleeds,
          "Elev", int(elevation * 500), "Temp", temp, "QNH", qnh, "ULD", final_uld, "Test case",
          test_case_number)

    wind_formula_ULD = wind_correct_formulated(final_uld, head_tail, flap)
    print(head_tail, "WIND COMP", wind_formula_ULD, "CORRECTED FOR WIND")

    corrected_for_slope = int(slope_corrected(slope, wind_formula_ULD, flap))
    print(slope, "SLOPE giving", corrected_for_slope, "CORRECTED FOR SLOPE")

    vapp, vref, vref_ice = get_v_speeds(weight, flap, vref_addit, ice, ab_fctr)

    abnormal_dist, abnormal_multiplier, can_land_in_this_config = abnormal_factor(ab_fctr, corrected_for_slope,
                                                                                  flap, ice)
    corrected_for_vapp = vapp_corrections(abnormal_dist, vref_addit, wet_dry)
    print("Are we able to land in this current configuration?", can_land_in_this_config)

    operation_fact_corrected_ld = company_addit_dry_wet(corrected_for_vapp)
    print(f"After adding the company 15% we get {operation_fact_corrected_ld}")

    ntop, mtop = get_torque_limits(temp, pressure_altitude, vapp, bleeds)
    print(ntop, mtop, "Torque figures")

    oei_climb_grad = get_oei_climb(temp, elevation, flap, weight)
    print(oei_climb_grad, "% OEI climb grad")

    max_wat_weight, MLDW, off_chart = get_wat_limit(temp, flap, ice, bleeds, pressure_altitude, test_case_number)
    print("BLEEDS", bleeds, "TEMP", temp, "PRESS ALT", pressure_altitude, "Max WAT weight", max_wat_weight, MLDW,
          "MLDW")

    max_field_based_wt = max_landing_wt_lda(lda, operation_fact_corrected_ld, flap, weight, final_uld)

    max_brake_nrg_weight = max_brake_energy_wt(flap, temp, elevation, weight, head_tail)

    max_weight = final_max_weight(max_wat_weight, max_field_based_wt, max_brake_nrg_weight, MLDW, off_chart)
    print(max_weight, "MAX WEIGHT")

    if head_tail < -20:
        head_tail = str(head_tail) + '*'
        can_land_in_this_config = False
    if crosswind > 36:
        wind_speed = str(wind_speed) + f" XW is {crosswind}*"  # Will make the wind component field go red
        can_land_in_this_config = False

    all_excel_data["Test Case Number"].append(test_case_number)
    all_excel_data["Airport Code"].append(airport_code)
    all_excel_data["Destination"].append(destination)
    all_excel_data["Runway"].append(runway)
    all_excel_data["Elevation"].append(elevation * 500)
    all_excel_data["LDA"].append(lda)
    all_excel_data["Slope"].append(slope)
    all_excel_data["Grooved/Ungrooved"].append(grooved_ungrooved)
    all_excel_data["Wind Direction"].append(wind_direction)
    all_excel_data["Wind Speed"].append(wind_speed)
    all_excel_data['"HW (+) / TW (-) Comp"'].append(head_tail)
    all_excel_data["Temp"].append(temp)
    all_excel_data["QNH"].append(qnh)
    all_excel_data["Dry/Wet"].append(wet_dry)
    all_excel_data["Weight"].append(weight)
    all_excel_data["VREF Additive"].append(vref_addit)
    all_excel_data["Flaps"].append(flap)
    all_excel_data["Bleeds"].append(bleeds)
    all_excel_data["Ice protection"].append(ice)
    all_excel_data["Pressure Altitude"].append(pressure_altitude)

    if not can_land_in_this_config:  # due to the config being not allowed for particular non normal
        ab_fctr = ab_fctr + "*"  # Will make the non-normal field go red
        abnormal_multiplier = pd.NA
        max_weight = pd.NA
        final_uld = pd.NA
        corrected_for_vapp = pd.NA
        operation_fact_corrected_ld = pd.NA
        vapp = pd.NA
        vref = pd.NA
        vref_ice = pd.NA

    all_excel_data["Abnormality"].append(ab_fctr)
    all_excel_data["Factor Applied"].append(abnormal_multiplier)

    all_excel_data["MLDW"].append(max_weight)
    all_excel_data["NTOP"].append(ntop)
    all_excel_data["MTOP"].append(mtop)
    all_excel_data["Unfactored ULD"].append(final_uld)
    all_excel_data["ULD"].append(corrected_for_vapp)
    all_excel_data["LDR"].append(operation_fact_corrected_ld)

    all_excel_data["Vapp"].append(vapp)
    all_excel_data["VREF"].append(vref)
    all_excel_data["VREF ICE"].append(vref_ice)
    all_excel_data["OEI Gradient"].append(oei_climb_grad)


for row_number in range(len(Q400)):
    all_data(Q400.loc[row_number])


def write_to_excel(all_exc):
    # Create a Pandas Excel writer using XlsxWriter as the engine.
    writer = pd.ExcelWriter('300_NNORMAL_run.xlsx')
    # Create a Pandas dataframe from the data
    df = pd.DataFrame(all_exc)
    # Convert the dataframe to an XlsxWriter Excel object.
    df = df.style.applymap(lambda x: 'background-color: red' if '*' in str(x) else ('background-color: orange' if
                                                                                    '^' in str(x) else ''))
    df.to_excel(writer, sheet_name='Completed Tests 300', index=False)
    # Close the Pandas Excel writer and output the Excel file.
    writer.close()


write_to_excel(all_excel_data)
