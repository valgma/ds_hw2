import logging
SERV_EXCHANGE = 'servers'
DELIM = "/"
KEEPALIVE = 5
TIMEOUT = KEEPALIVE*3

def make_logger():
    FORMAT = '%(asctime)-15s %(levelname)s %(message)s'
    logging.basicConfig(level=logging.DEBUG,format=FORMAT)
    LOG = logging.getLogger()
    logging.getLogger("pika").propagate = False
    return LOG

def validate_ships(ships, rows, cols, req_ships):
    #if len(ships) > 0:
    #    return True #TODO: temporary
    # req_ships = {5:1, 4:2, 3:3, 2:4}
    found_ships = []
    # check for single ships
    for (row, col) in ships:
        w = (row, col-1) not in ships
        e = (row, col+1) not in ships
        n = (row-1, col) not in ships
        s = (row+1, col) not in ships
        if all((w,e,n,s)):
            print "single ships not allowed!"
            return False

    # look through horisontally
    for row in range(rows):
        cur_ship = []
        for col in range(cols):
            if (row, col) in ships:
                cur_ship.append((row, col))
            else:
                if len(cur_ship) > 1:
                    found_ships.append(cur_ship[:])
                cur_ship = []
        if len(cur_ship) > 1:
            found_ships.append(cur_ship[:])

    # look through vertically
    for col in range(cols):
        cur_ship = []
        for row in range(rows):
            if (row, col) in ships:
                cur_ship.append((row, col))
            else:
                if len(cur_ship) > 1:
                    found_ships.append(cur_ship[:])
                cur_ship = []
        if len(cur_ship) > 1:
            found_ships.append(cur_ship[:])

    # order ships by length
    found_ships.sort(key=lambda x: len(x), reverse=True)

    # print ships
    print "SHIPS"
    for ship in found_ships:
        print ship

    # check number and lengths of ships
    ship_lens = {2:0, 3:0, 4:0, 5:0}
    for ship in found_ships:
        l = len(ship)
        if l in ship_lens:
            ship_lens[l] += 1
        else:
            ship_lens[l] = 1

    if ship_lens != req_ships:
        print "Wrong ship number!"
        return False

    # check for touching ships
    def has_overlap(cells, cur_ship):
        for cell in cells:
            for ship in found_ships:
                if ship != cur_ship:
                    if cell in ship:
                        return True
        return False

    for ship in found_ships:
        for (row, col) in ship:
            w = (row, col-1)
            e = (row, col+1)
            n = (row-1, col)
            s = (row+1, col)
            nw = (row-1, col-1)
            ne = (row-1, col+1)
            sw = (row+1, col-1)
            se = (row+1, col+1)
            cells = (w,e,n,s,nw,ne,sw,se)
            if has_overlap(cells, ship):
                print "Touching ships not allowed!"
                return False

    print "Ship conf OK"
    return True
