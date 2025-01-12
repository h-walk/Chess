# chess_enhanced_truth_tables.py

import sys

############################################
# Precompute moves (truth tables) for each piece
############################################

def in_bounds(r, c):
    return 0 <= r < 8 and 0 <= c < 8

def build_knight_moves():
    """
    knight_moves[(r,c)] = [(r2,c2), ...] for all squares a knight can jump to from (r,c).
    """
    moves = {}
    offsets = [
        (-2, -1), (-2, 1), (-1, -2), (-1, 2),
        (1, -2), (1, 2), (2, -1), (2, 1)
    ]
    for r in range(8):
        for c in range(8):
            possible = []
            for dr, dc in offsets:
                rr, cc = r + dr, c + dc
                if in_bounds(rr, cc):
                    possible.append((rr, cc))
            moves[(r, c)] = possible
    return moves

def build_king_moves():
    """
    king_moves[(r,c)] = [(r2,c2), ...] for all squares a king can move to from (r,c).
    Doesn’t handle castling (we treat that separately).
    """
    moves = {}
    offsets = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1),           (0, 1),
        (1, -1),  (1, 0),  (1, 1)
    ]
    for r in range(8):
        for c in range(8):
            possible = []
            for dr, dc in offsets:
                rr, cc = r + dr, c + dc
                if in_bounds(rr, cc):
                    possible.append((rr, cc))
            moves[(r, c)] = possible
    return moves

def build_sliding_moves():
    """
    For rooks, bishops, queens we store 'rays' in each direction from each square.
    e.g. rook_slides[(r,c)] = [
      [ (r+1, c), (r+2, c), ... ] up to board edge,
      [ (r-1, c), (r-2, c), ... ],
      [ (r, c+1), (r, c+2), ... ],
      [ (r, c-1), (r, c-2), ... ]
    ]
    And similarly for bishops. Queens is union of rook + bishop directions.
    """
    rook_slides = {}
    bishop_slides = {}

    # Directions
    rook_dirs = [(1,0), (-1,0), (0,1), (0,-1)]
    bishop_dirs = [(1,1), (1,-1), (-1,1), (-1,-1)]

    for r in range(8):
        for c in range(8):
            # Build rook rays
            rook_rays = []
            for (dr, dc) in rook_dirs:
                ray = []
                rr, cc = r + dr, c + dc
                while in_bounds(rr, cc):
                    ray.append((rr, cc))
                    rr += dr
                    cc += dc
                rook_rays.append(ray)
            rook_slides[(r,c)] = rook_rays

            # Build bishop rays
            bishop_rays = []
            for (dr, dc) in bishop_dirs:
                ray = []
                rr, cc = r + dr, c + dc
                while in_bounds(rr, cc):
                    ray.append((rr, cc))
                    rr += dr
                    cc += dc
                bishop_rays.append(ray)
            bishop_slides[(r,c)] = bishop_rays

    return rook_slides, bishop_slides


# Now we build the tables up front
KNIGHT_MOVES = build_knight_moves()
KING_MOVES = build_king_moves()
ROOK_SLIDES, BISHOP_SLIDES = build_sliding_moves()

def in_bounds(r, c):
    return 0 <= r < 8 and 0 <= c < 8

############################################
# Original data structures
############################################

STARTING_BOARD = [
    list("rnbqkbnr"),
    list("pppppppp"),
    list("........"),
    list("........"),
    list("........"),
    list("........"),
    list("PPPPPPPP"),
    list("RNBQKBNR"),
]

# We'll track castling rights for each side.
# (king_side, queen_side)
CASTLE_RIGHTS = {
    "white": [True, True],
    "black": [True, True]
}

def copy_board(board):
    return [row[:] for row in board]

def get_piece_color(piece):
    if piece == ".":
        return None
    return "white" if piece.isupper() else "black"

def is_white(piece):
    return piece.isupper()

def is_black(piece):
    return piece.islower()

def print_board(board):
    print("  a b c d e f g h")
    for i in range(8):
        row_str = str(8 - i) + " "
        for j in range(8):
            row_str += board[i][j] + " "
        print(row_str + str(8 - i))
    print("  a b c d e f g h")

def parse_move(move):
    """
    Input format: e2 e4
    Returns: ((r1, c1), (r2, c2)) in 0-based indexing or (None, None) if invalid.
    """
    try:
        start, end = move.split()
        c1 = ord(start[0]) - ord('a')
        r1 = 8 - int(start[1])
        c2 = ord(end[0]) - ord('a')
        r2 = 8 - int(end[1])
        return (r1, c1), (r2, c2)
    except:
        return None, None

############################################
# Validation and movement
############################################

def find_king_position(board, color):
    # Return (row, col) of the king of given color
    king_char = 'K' if color == 'white' else 'k'
    for r in range(8):
        for c in range(8):
            if board[r][c] == king_char:
                return (r, c)
    return None

def in_check(board, color):
    """
    Return True if 'color' is in check on 'board'.
    We'll see if the king can be captured by any enemy piece.
    """
    king_pos = find_king_position(board, color)
    if king_pos is None:
        return False

    # Check all squares for enemy pieces that can move to king_pos
    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if piece != '.' and get_piece_color(piece) != color:
                if is_valid_move(board, (r,c), king_pos, get_piece_color(piece) == 'white',
                                 en_passant_target=None, checking_check=False):
                    return True
    return False

def is_valid_move(board, start, end, turn_white, en_passant_target, checking_check=True):
    r1, c1 = start
    r2, c2 = end

    if not in_bounds(r1, c1) or not in_bounds(r2, c2):
        return False

    piece = board[r1][c1]
    if piece == '.':
        return False

    piece_color = "white" if is_white(piece) else "black"
    if turn_white and piece_color != "white":
        return False
    if (not turn_white) and piece_color != "black":
        return False

    target = board[r2][c2]
    if target != '.' and get_piece_color(target) == piece_color:
        return False  # can’t capture your own piece

    # Validate by piece type
    p = piece.upper()

    if p == 'P':
        if not valid_pawn_move(board, start, end, turn_white, en_passant_target):
            return False
    elif p == 'N':
        if end not in KNIGHT_MOVES[start]:
            return False
    elif p == 'B':
        if not valid_bishop_move(board, start, end):
            return False
    elif p == 'R':
        if not valid_rook_move(board, start, end):
            return False
    elif p == 'Q':
        if not valid_queen_move(board, start, end):
            return False
    elif p == 'K':
        # normal king move (castling is handled separately)
        if end not in KING_MOVES[start]:
            return False
    else:
        return False

    # If checking_check = False, skip the next step
    if not checking_check:
        return True

    # Make sure it doesn't leave our king in check
    temp = copy_board(board)
    temp[r1][c1] = '.'

    # handle en passant capture
    if p == 'P':
        # if en passant
        if en_passant_target is not None:
            ep_r, ep_c = en_passant_target
            if (r2, c2) == (ep_r, ep_c) and c1 != c2 and temp[r2][c2] == '.':
                # remove the captured pawn
                direction = -1 if turn_white else 1
                temp[r1][c2] = '.'

    temp[r2][c2] = piece
    if in_check(temp, piece_color):
        return False

    return True

def valid_pawn_move(board, start, end, turn_white, en_passant_target):
    r1, c1 = start
    r2, c2 = end
    piece = board[r1][c1]

    direction = -1 if turn_white else 1  # white moves up (-1), black down (+1)
    start_row = 6 if turn_white else 1
    enemy_color = "black" if turn_white else "white"

    # Single-step
    if c1 == c2 and (r2 == r1 + direction):
        if board[r2][c2] == '.':
            return True

    # Double-step
    if c1 == c2 and r1 == start_row and r2 == r1 + 2*direction:
        mid_r = r1 + direction
        if board[mid_r][c1] == '.' and board[r2][c2] == '.':
            return True

    # Diagonal capture or en passant
    if abs(c2 - c1) == 1 and (r2 == r1 + direction):
        # Normal capture
        if board[r2][c2] != '.' and get_piece_color(board[r2][c2]) == enemy_color:
            return True
        # En passant
        if en_passant_target is not None:
            if (r2, c2) == en_passant_target and board[r2][c2] == '.':
                return True

    return False

def valid_rook_move(board, start, end):
    """
    Use the precomputed rook_slides to see if (end) is in one of the rays from (start).
    Then check that the path is not blocked.
    """
    r1, c1 = start
    r2, c2 = end

    # Look through each direction-rain for start
    for ray in ROOK_SLIDES[start]:
        if end in ray:
            # check if anything blocks
            # move along the ray until we hit 'end' or a piece
            for sq in ray:
                if sq == end:
                    # we made it to end w/out collision
                    return True
                if board[sq[0]][sq[1]] != '.':
                    # if we bump into a piece before end, blocked
                    return False
    return False

def valid_bishop_move(board, start, end):
    """
    Use bishop_slides, check for block.
    """
    r1, c1 = start
    for ray in BISHOP_SLIDES[start]:
        if end in ray:
            for sq in ray:
                if sq == end:
                    return True
                if board[sq[0]][sq[1]] != '.':
                    return False
    return False

def valid_queen_move(board, start, end):
    """
    A queen is rook + bishop. So we check both.
    """
    # We can do it simply by combining both checks, or build a union of rook+bishop slides.
    # Let’s do the quick method: if rook or bishop logic is satisfied => valid.
    if valid_rook_move(board, start, end):
        return True
    if valid_bishop_move(board, start, end):
        return True
    return False

############################################
# Castling, en passant, promotion
############################################

def can_castle(board, color, side, castling_rights):
    row = 7 if color == 'white' else 0
    king_char = 'K' if color == 'white' else 'k'
    if side == 'king':
        if not castling_rights[0]:
            return False
        # squares: e->f->g must be empty
        if board[row][4] != king_char:
            return False
        if board[row][5] != '.' or board[row][6] != '.':
            return False
        # check if rook is correct color
        if not (board[row][7] in ('R', 'r') and get_piece_color(board[row][7]) == color):
            return False
        # check squares not in check
        temp = copy_board(board)
        # king e->f
        temp[row][4], temp[row][5] = '.', king_char
        if in_check(temp, color):
            return False
        # king f->g
        temp[row][5], temp[row][6] = '.', king_char
        if in_check(temp, color):
            return False
        return True
    else:  # queen side
        if not castling_rights[1]:
            return False
        if board[row][4] != king_char:
            return False
        if board[row][3] != '.' or board[row][2] != '.' or board[row][1] != '.':
            return False
        if not (board[row][0] in ('R', 'r') and get_piece_color(board[row][0]) == color):
            return False
        temp = copy_board(board)
        # e->d
        temp[row][4], temp[row][3] = '.', king_char
        if in_check(temp, color):
            return False
        # d->c
        temp[row][3], temp[row][2] = '.', king_char
        if in_check(temp, color):
            return False
        return True

def do_castle(board, color, side):
    row = 7 if color == 'white' else 0
    king_char = 'K' if color == 'white' else 'k'
    if side == 'king':
        # e->g, h->f
        board[row][4] = '.'
        board[row][6] = king_char
        board[row][5] = board[row][7]
        board[row][7] = '.'
    else:
        # e->c, a->d
        board[row][4] = '.'
        board[row][2] = king_char
        board[row][3] = board[row][0]
        board[row][0] = '.'

def promotion_choice(color):
    """
    For now, prompt the user to choose a promotion piece: Q, R, B, or N.
    Return the appropriate uppercase/lowercase letter.
    """
    while True:
        choice = input(f"Promote to Q, R, B, or N? ").upper()
        if choice in ['Q','R','B','N']:
            return choice if color == "white" else choice.lower()
        print("Invalid choice, please enter Q, R, B, or N.")

############################################
# Execute moves
############################################

def move_with_extras(board, start, end, turn_white, en_passant_target, castling_rights):
    """
    Perform the move, handling en passant, castling, promotion.
    Returns (new_en_passant_target, updated_castling_rights).
    """
    r1, c1 = start
    r2, c2 = end
    piece = board[r1][c1]
    p = piece.upper()
    color = 'white' if is_white(piece) else 'black'

    # Reset unless we do a 2-square pawn move
    new_en_passant = None

    # Attempt castling if king moves from e->g or e->c in starting row
    row = 7 if color == 'white' else 0
    if p == 'K' and r1 == row and c1 == 4:
        # king side
        if (r2, c2) == (row, 6) and can_castle(board, color, 'king', castling_rights[color]):
            do_castle(board, color, 'king')
            castling_rights[color] = [False, False]
            return None, castling_rights
        # queen side
        if (r2, c2) == (row, 2) and can_castle(board, color, 'queen', castling_rights[color]):
            do_castle(board, color, 'queen')
            castling_rights[color] = [False, False]
            return None, castling_rights

    # Regular move
    board[r1][c1] = '.'
    # En passant capture
    if p == 'P':
        if en_passant_target is not None:
            ep_r, ep_c = en_passant_target
            if (r2, c2) == (ep_r, ep_c) and c1 != c2 and board[r2][c2] == '.':
                # remove the captured pawn
                board[r1][c2] = '.'
        # If double-step, set en_passant_target
        direction = -1 if color == 'white' else 1
        if abs(r2 - r1) == 2:
            mid_r = (r1 + r2) // 2
            new_en_passant = (mid_r, c1)

    board[r2][c2] = piece

    # Pawn promotion
    if p == 'P':
        if color == 'white' and r2 == 0:
            board[r2][c2] = promotion_choice(color)
        elif color == 'black' and r2 == 7:
            board[r2][c2] = promotion_choice(color)

    # Update castling rights if king/rook moved
    if p == 'K':
        castling_rights[color] = [False, False]
    elif p == 'R':
        # if it was the a/h rook
        if color == 'white':
            if r1 == 7 and c1 == 0:  # Q-side
                castling_rights[color][1] = False
            elif r1 == 7 and c1 == 7:  # K-side
                castling_rights[color][0] = False
        else:
            if r1 == 0 and c1 == 0:
                castling_rights[color][1] = False
            elif r1 == 0 and c1 == 7:
                castling_rights[color][0] = False

    return new_en_passant, castling_rights

############################################
# Main game loop
############################################

def main():
    board = copy_board(STARTING_BOARD)
    turn_white = True
    en_passant_target = None
    castling_rights = {
        "white": CASTLE_RIGHTS["white"][:],
        "black": CASTLE_RIGHTS["black"][:]
    }

    while True:
        print_board(board)
        player_color = "white" if turn_white else "black"
        player_str = "White" if turn_white else "Black"

        # Check if in check
        if in_check(board, player_color):
            print(f"{player_str} is in check!")

        move_input = input(f"{player_str}'s move (e.g. 'e2 e4', or 'quit'): ")
        if move_input.lower() == 'quit':
            print("Goodbye.")
            sys.exit()

        start, end = parse_move(move_input)
        if start is None or end is None:
            print("Invalid input format. Try again.")
            continue

        if is_valid_move(board, start, end, turn_white, en_passant_target):
            # Check king safety after the move
            temp_board = copy_board(board)
            _, temp_cr = move_with_extras(
                temp_board, start, end, turn_white,
                en_passant_target,
                {
                    "white": castling_rights["white"][:],
                    "black": castling_rights["black"][:]
                }
            )
            if in_check(temp_board, player_color):
                print("Illegal: that would leave your king in check.")
                continue

            # If good, actually make the move
            en_passant_target, castling_rights[player_color] = move_with_extras(
                board, start, end, turn_white, en_passant_target,
                castling_rights[player_color]
            )

            turn_white = not turn_white
        else:
            print("Illegal move. Try again.")

if __name__ == "__main__":
    main()  
