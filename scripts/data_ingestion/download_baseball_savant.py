#!/usr/bin/env python3
"""
Download Baseball Savant Statcast data by iterating over years.

This script fetches data from Baseball Savant custom leaderboards for multiple years.
"""

import argparse
import sys
import time
from pathlib import Path

try:
    import pandas as pd
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: Required libraries not installed.")
    print("Install with: pip install requests beautifulsoup4 pandas")
    sys.exit(1)


# Base selections for comprehensive batter metrics
BATTER_SELECTIONS = "player_age%2Cab%2Cpa%2Chit%2Csingle%2Cdouble%2Ctriple%2Chome_run%2Cstrikeout%2Cwalk%2Ck_percent%2Cbb_percent%2Cbatting_avg%2Cslg_percent%2Con_base_percent%2Con_base_plus_slg%2Cisolated_power%2Cbabip%2Cb_rbi%2Cb_lob%2Cb_total_bases%2Cr_total_caught_stealing%2Cr_total_stolen_base%2Cb_ab_scoring%2Cb_ball%2Cb_called_strike%2Cb_catcher_interf%2Cb_foul%2Cb_foul_tip%2Cb_game%2Cb_gnd_into_dp%2Cb_gnd_into_tp%2Cb_gnd_rule_double%2Cb_hit_by_pitch%2Cb_hit_ground%2Cb_hit_fly%2Cb_hit_into_play%2Cb_hit_line_drive%2Cb_hit_popup%2Cb_out_fly%2Cb_out_ground%2Cb_out_line_drive%2Cb_out_popup%2Cb_intent_ball%2Cb_intent_walk%2Cb_interference%2Cb_pinch_hit%2Cb_pinch_run%2Cb_pitchout%2Cb_played_dh%2Cb_sac_bunt%2Cb_sac_fly%2Cb_swinging_strike%2Cr_caught_stealing_2b%2Cr_caught_stealing_3b%2Cr_caught_stealing_home%2Cr_defensive_indiff%2Cr_interference%2Cr_pickoff_1b%2Cr_pickoff_2b%2Cr_pickoff_3b%2Cr_run%2Cr_stolen_base_2b%2Cr_stolen_base_3b%2Cr_stolen_base_home%2Cb_total_ball%2Cb_total_sacrifices%2Cb_total_strike%2Cb_total_swinging_strike%2Cb_total_pitches%2Cr_stolen_base_pct%2Cr_total_pickoff%2Cb_reached_on_error%2Cb_walkoff%2Cb_reached_on_int%2Cxba%2Cxslg%2Cwoba%2Cxwoba%2Cxobp%2Cxiso%2Cwobacon%2Cxwobacon%2Cbacon%2Cxbacon%2Cxbadiff%2Cxslgdiff%2Cwobadiff%2Cavg_swing_speed%2Cfast_swing_rate%2Cblasts_contact%2Cblasts_swing%2Csquared_up_contact%2Csquared_up_swing%2Cavg_swing_length%2Cswords%2Cattack_angle%2Cattack_direction%2Cideal_angle_rate%2Cvertical_swing_path%2Cexit_velocity_avg%2Claunch_angle_avg%2Csweet_spot_percent%2Cbarrel%2Cbarrel_batted_rate%2Csolidcontact_percent%2Cflareburner_percent%2Cpoorlyunder_percent%2Cpoorlytopped_percent%2Cpoorlyweak_percent%2Chard_hit_percent%2Cavg_best_speed%2Cavg_hyper_speed%2Cz_swing_percent%2Cz_swing_miss_percent%2Coz_swing_percent%2Coz_swing_miss_percent%2Coz_contact_percent%2Cout_zone_swing_miss%2Cout_zone_swing%2Cout_zone_percent%2Cout_zone%2Cmeatball_swing_percent%2Cmeatball_percent%2Cpitch_count_offspeed%2Cpitch_count_fastball%2Cpitch_count_breaking%2Cpitch_count%2Ciz_contact_percent%2Cin_zone_swing_miss%2Cin_zone_swing%2Cin_zone_percent%2Cin_zone%2Cedge_percent%2Cedge%2Cwhiff_percent%2Cswing_percent%2Cpull_percent%2Cstraightaway_percent%2Copposite_percent%2Cbatted_ball%2Cf_strike_percent%2Cgroundballs_percent%2Cgroundballs%2Cflyballs_percent%2Cflyballs%2Clinedrives_percent%2Clinedrives%2Cpopups_percent%2Cpopups%2Cpop_2b_sba_count%2Cpop_2b_sba%2Cpop_2b_sb%2Cpop_2b_cs%2Cpop_3b_sba_count%2Cpop_3b_sba%2Cpop_3b_sb%2Cpop_3b_cs%2Cexchange_2b_3b_sba%2Cmaxeff_arm_2b_3b_sba%2Cn_outs_above_average%2Cn_fieldout_5stars%2Cn_opp_5stars%2Cn_5star_percent%2Cn_fieldout_4stars%2Cn_opp_4stars%2Cn_4star_percent%2Cn_fieldout_3stars%2Cn_opp_3stars%2Cn_3star_percent%2Cn_fieldout_2stars%2Cn_opp_2stars%2Cn_2star_percent%2Cn_fieldout_1stars%2Cn_opp_1stars%2Cn_1star_percent%2Crel_league_reaction_distance%2Crel_league_burst_distance%2Crel_league_routing_distance%2Crel_league_bootup_distance%2Cf_bootup_distance%2Cn_bolts%2Chp_to_1b"


def download_baseball_savant_year(year: int, data_type: str = "batter") -> bool:
    """Download Baseball Savant data for a single year."""

    # Use the standard URL without CSV parameter
    url = f"https://baseballsavant.mlb.com/leaderboard/custom?year={year}&type={data_type}&filter=&min=q&selections={BATTER_SELECTIONS}&chart=false&x=player_age&y=player_age&r=no&chartType=beeswarm&sort=1&sortDir=desc"

    print(f"Downloading {data_type} data for {year}...")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=120)
        response.raise_for_status()

        # Baseball Savant embeds data in JavaScript as JSON
        # Look for the data in the HTML response
        import json
        import re

        # The data is embedded in a script tag with a variable assignment
        # Look for patterns like: var data = [{...}] or data: [{...}]

        # Try multiple patterns to find the data
        patterns = [
            r"var\s+data\s*=\s*(\[.*?\]);",
            r"data\s*:\s*(\[.*?\]),",
            r"const\s+data\s*=\s*(\[.*?\]);",
            r"leaderboardData\s*=\s*(\[.*?\]);",
        ]

        data = None
        for pattern in patterns:
            matches = re.findall(pattern, response.text, re.DOTALL)
            if matches:
                try:
                    json_str = matches[0]
                    data = json.loads(json_str)
                    if data:
                        break
                except json.JSONDecodeError:
                    continue

        if not data:
            # Try finding JSON array with player_name as fallback
            pattern = r'\[{.*?"player_name".*?\}]'
            matches = re.findall(pattern, response.text, re.DOTALL)
            if matches:
                try:
                    json_str = matches[0]
                    data = json.loads(json_str)
                except json.JSONDecodeError:
                    pass

        if not data:
            print(f"  ⚠️  Could not find data in HTML for {year}")
            return False

        # Create DataFrame
        df = pd.DataFrame(data)

        # Save to CSV
        output_dir = Path(__file__).resolve().parents[1] / "data" / "baseball_savant"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"baseball_savant_{data_type}_{year}.csv"
        df.to_csv(output_file, index=False)

        print(f"  ✅ Saved {len(df)} rows to {output_file}")
        return True

    except requests.exceptions.Timeout:
        print(f"  ❌ Request timed out for {year}")
        return False
    except json.JSONDecodeError as e:
        print(f"  ❌ JSON decode error for {year}: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error for {year}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Download Baseball Savant data for multiple years")
    parser.add_argument(
        "--year-start", type=int, default=2008, help="Start year (Statcast began in 2008)"
    )
    parser.add_argument("--year-end", type=int, default=2026, help="End year")
    parser.add_argument(
        "--type", choices=["batter", "pitcher", "both"], default="both", help="Data type"
    )
    args = parser.parse_args()

    years = list(range(args.year_start, args.year_end + 1))

    print(f"Downloading Baseball Savant data for years: {years}")
    print(f"Data directory: {Path(__file__).resolve().parents[1] / 'data' / 'baseball_savant'}")
    print("=" * 60)

    results = {}

    for year in years:
        if args.type in ["batter", "both"]:
            success = download_baseball_savant_year(year, "batter")
            results[f"batter_{year}"] = success
            time.sleep(2)  # Rate limiting

        if args.type in ["pitcher", "both"]:
            success = download_baseball_savant_year(year, "pitcher")
            results[f"pitcher_{year}"] = success
            time.sleep(2)  # Rate limiting

    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)
    for key, success in results.items():
        status = "✅" if success else "❌"
        print(f"{status} {key}")
    print("=" * 60)


if __name__ == "__main__":
    main()
