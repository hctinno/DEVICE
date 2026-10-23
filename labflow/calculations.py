"""Physical arithmetic only; no FCC limits or unverified method defaults."""
import math


def number(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('A finite numeric value is required')
    return float(value)


def calculate(calculator,data):
    if not isinstance(data,dict):raise ValueError('Observation must be an object')
    try:
        reading=number(data['reading'])
        if calculator=='emc_field_strength':
            if data.get('instrument_corrections_applied') is not False:
                raise ValueError('Declare uncorrected instrument data; applied or unknown corrections need another method')
            if data['unit'] not in {'dBuV','dBµV'}:raise ValueError('Field-strength input must be dBuV')
            result=reading+number(data['antenna_factor_db_per_m'])+number(data['cable_loss_db'])-number(data['preamp_gain_db'])
            unit='dBuV/m'
        elif calculator=='rf_power':
            if data['unit']!='dBm':raise ValueError('RF power input must be dBm')
            result=10.0**((reading-30.0)/10.0);unit='W'
            if result==0:raise ValueError('Power conversion underflow')
        else:raise ValueError('Unsupported calculator: '+str(calculator))
        return {'value':number(result),'unit':unit}
    except (KeyError,OverflowError,TypeError) as exc:
        raise ValueError('Missing or invalid calculation input: '+str(exc)) from exc
