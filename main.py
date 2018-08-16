from retrosheet import Parser, Event

if __name__ == '__main__':
    parser = Parser()
    info, starting, plays, er, subs, comments, rosters, teams = parser.parse_years(yearFrom=2017, yearTo=2017, save_to_csv=True)

    event_sequence = [
    'S9','S7.1-2','34/SH.2-3;1-2','S9.3-H;2-3','W.1-2''S8.3-H;2-H;1X3(8254)','4'
    ]

    play = {'B': 1,'1': 0,'2': 0,'3': 0,'H': 0, 'out': 0, 'run': 0}
    event = Event('NP', play)

    for string in event_sequence:
        event.str = string
        event.decipher()
    #    event._print_diamond()