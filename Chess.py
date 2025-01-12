import sys

########################################
# Precompute piece moves (truth tables)
########################################

def in_bounds(r, c):
    return 0 <= r < 8 and 0 <= c < 8

def build_knight_moves():
    offsets = [
        (-2, -1), (-2, 1), (-1, -2), (-1, 2),
        (1, -2), (1, 2), (2, -1), (2, 1)
    ]
    moves = {}
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
    offsets = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1),           (0, 1),
        (1, -1),  (1, 0),  (1, 1)
    ]
    moves = {}
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
    rook_dirs = [(1,0), (-1,0), (0,1), (0,-1)]
    bishop_dirs = [(1,1), (1,-1), (-1,1), (-1,-1)]
    rook_slides = {}
    bishop_slides = {}
    for r in range(8):
        for c in range(8):
            # Rook rays
            rays_r = []
            for dr, dc in rook_dirs:
                ray = []
                rr, cc = r + dr, c + dc
                while in_bounds(rr, cc):
                    ray.append((rr, cc))
                    rr += dr
                    cc += dc
                rays_r.append(ray)
            rook_slides[(r,c)] = rays_r

            # Bishop rays
            rays_b = []
            for dr, dc in bishop_dirs:
                ray = []
                rr, cc = r + dr, c + dc
                while in_bounds(rr, cc):
                    ray.append((rr, cc))
                    rr += dr
                    cc += dc
                rays_b.append(ray)
            bishop_slides[(r,c)] = rays_b

    return rook_slides, bishop_slides

KNIGHT_MOVES = build_knight_moves()
KING_MOVES   = build_king_moves()
ROOK_SLIDES, BISHOP_SLIDES = build_sliding_moves()

########################################
# Board setup + utilities
########################################

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

# castling_rights[color] = [king_side, queen_side]
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

def parse_move(move_str):
    try:
        start_str, end_str = move_str.split()
        c1 = ord(start_str[0].lower()) - ord('a')
        r1 = 8 - int(start_str[1])
        c2 = ord(end_str[0].lower()) - ord('a')
        r2 = 8 - int(end_str[1])
        return (r1, c1), (r2, c2)
    except:
        return None, None

########################################
# Check logic
########################################

def find_king_position(board, color):
    king_char = 'K' if color == 'white' else 'k'
    for r in range(8):
        for c in range(8):
            if board[r][c] == king_char:
                return (r, c)
    return None

def square_attacked_by(board, r, c, color):
    """Returns True if a piece of 'color' can legally move to (r,c)."""
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece != '.' and get_piece_color(piece) == color:
                if is_valid_move(
                    board, (row, col), (r, c),
                    color == "white", 
                    en_passant_target=None,
                    castling_rights=None,
                    checking_check=False
                ):
                    return True
    return False

def in_check(board, color):
    """True if 'color' is in check on 'board'."""
    king_pos = find_king_position(board, color)
    if not king_pos:
        return False
    (r, c) = king_pos
    opponent = 'white' if color == 'black' else 'black'
    return square_attacked_by(board, r, c, opponent)

########################################
# Move validation
########################################

def is_valid_move(
    board, start, end, turn_white,
    en_passant_target, castling_rights,
    checking_check=True
):
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
    # Can't capture your own piece
    if target != '.' and get_piece_color(target) == piece_color:
        return False

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
        # Normal king moves
        if end in KING_MOVES[start]:
            pass
        else:
            # Attempting castling
            color = "white" if turn_white else "black"
            side = None
            if (r2, c2) == ((7, 6) if color == "white" else (0, 6)):
                side = 'king'
            elif (r2, c2) == ((7, 2) if color == "white" else (0, 2)):
                side = 'queen'
            if side:
                if castling_rights is None:
                    return False
                color_castle_rights = castling_rights.get(color, [False, False])
                if not can_castle(board, color, side, color_castle_rights):
                    return False
            else:
                return False
    else:
        return False

    if not checking_check:
        return True

    # Check if move leaves our king in check
    temp = copy_board(board)
    temp_cr = {
        "white": castling_rights["white"][:] if castling_rights else [True, True],
        "black": castling_rights["black"][:] if castling_rights else [True, True]
    }
    temp_enp, _ = move_with_extras(
        temp, start, end, turn_white,
        en_passant_target, temp_cr
    )
    if in_check(temp, piece_color):
        return False

    return True

def valid_pawn_move(board, start, end, turn_white, en_passant_target):
    r1, c1 = start
    r2, c2 = end
    piece = board[r1][c1]
    direction = -1 if turn_white else 1
    start_row = 6 if turn_white else 1
    enemy_color = 'black' if turn_white else 'white'

    # Single-step
    if c1 == c2 and (r2 == r1 + direction) and board[r2][c2] == '.':
        return True

    # Double-step
    if c1 == c2 and r1 == start_row and r2 == r1 + 2*direction:
        mid_r = r1 + direction
        if board[mid_r][c1] == '.' and board[r2][c2] == '.':
            return True

    # Diagonal capture or en passant
    if abs(c2 - c1) == 1 and r2 == r1 + direction:
        # Normal capture
        if board[r2][c2] != '.' and get_piece_color(board[r2][c2]) == enemy_color:
            return True
        # En passant
        if en_passant_target is not None:
            if (r2, c2) == en_passant_target and board[r2][c2] == '.':
                return True

    return False

def valid_rook_move(board, start, end):
    for ray in ROOK_SLIDES[start]:
        if end in ray:
            for sq in ray:
                if sq == end:
                    return True
                if board[sq[0]][sq[1]] != '.':
                    return False
    return False

def valid_bishop_move(board, start, end):
    for ray in BISHOP_SLIDES[start]:
        if end in ray:
            for sq in ray:
                if sq == end:
                    return True
                if board[sq[0]][sq[1]] != '.':
                    return False
    return False

def valid_queen_move(board, start, end):
    # Queen = Rook + Bishop
    if valid_rook_move(board, start, end):
        return True
    if valid_bishop_move(board, start, end):
        return True
    return False

########################################
# Castling, en passant, promotion
########################################

def can_castle(board, color, side, castling_rights):
    """
    Check if castling is possible for the given color and side.
    castling_rights is [king_side, queen_side].
    """
    row = 7 if color == 'white' else 0
    king_char = 'K' if color == 'white' else 'k'
    if side == 'king':
        if not castling_rights[0]:
            return False
        if board[row][4] != king_char:
            return False
        if board[row][5] != '.' or board[row][6] != '.':
            return False
        if not (board[row][7] in ('R','r') and get_piece_color(board[row][7]) == color):
            return False
        opponent = 'black' if color == 'white' else 'white'
        if in_check(board, color):
            return False
        if square_attacked_by(board, row, 5, opponent):
            return False
        if square_attacked_by(board, row, 6, opponent):
            return False
        return True
    else:  # queen-side
        if not castling_rights[1]:
            return False
        if board[row][4] != king_char:
            return False
        if board[row][3] != '.' or board[row][2] != '.' or board[row][1] != '.':
            return False
        if not (board[row][0] in ('R','r') and get_piece_color(board[row][0]) == color):
            return False
        opponent = 'black' if color == 'white' else 'white'
        if in_check(board, color):
            return False
        if square_attacked_by(board, row, 3, opponent):
            return False
        if square_attacked_by(board, row, 2, opponent):
            return False
        return True

def do_castle(board, color, side):
    row = 7 if color == 'white' else 0
    king_char = 'K' if color == 'white' else 'k'
    if side == 'king':
        board[row][4] = '.'
        board[row][6] = king_char
        board[row][5] = board[row][7]
        board[row][7] = '.'
    else:
        board[row][4] = '.'
        board[row][2] = king_char
        board[row][3] = board[row][0]
        board[row][0] = '.'

def promotion_choice(color):
    while True:
        choice = input(f"Promote to Q, R, B, or N? ").strip().upper()
        if choice in ['Q','R','B','N']:
            return choice if color == 'white' else choice.lower()
        print("Invalid choice, try Q, R, B, or N.")

########################################
# Move execution
########################################

def move_with_extras(board, start, end, turn_white, en_passant_target, castling_dict):
    r1, c1 = start
    r2, c2 = end
    piece = board[r1][c1]
    p = piece.upper()
    color = 'white' if is_white(piece) else 'black'
    row = 7 if color == 'white' else 0

    new_enp = None

    # Attempt castling
    if p == 'K' and (r1, c1) == (row, 4):
        if (r2, c2) == (row, 6) and can_castle(board, color, 'king', castling_dict[color]):
            do_castle(board, color, 'king')
            castling_dict[color] = [False, False]
            return None, castling_dict
        if (r2, c2) == (row, 2) and can_castle(board, color, 'queen', castling_dict[color]):
            do_castle(board, color, 'queen')
            castling_dict[color] = [False, False]
            return None, castling_dict

    # Regular move
    board[r1][c1] = '.'
    # En passant capture
    if p == 'P' and en_passant_target is not None:
        ep_r, ep_c = en_passant_target
        if (r2, c2) == (ep_r, ep_c) and c1 != c2 and board[r2][c2] == '.':
            board[r1][c2] = '.'  # remove jumped pawn

    board[r2][c2] = piece

    # 2-square pawn move => new en passant
    if p == 'P':
        direction = -1 if color=='white' else 1
        if abs(r2 - r1) == 2:
            mid_r = (r1 + r2) // 2
            new_enp = (mid_r, c1)

    # Pawn promotion
    if p == 'P':
        if color == 'white' and r2 == 0:
            board[r2][c2] = promotion_choice(color)
        elif color == 'black' and r2 == 7:
            board[r2][c2] = promotion_choice(color)

    # Revoke castling if king/rook moved
    if p == 'K':
        castling_dict[color] = [False, False]
    elif p == 'R':
        if color=='white':
            if (r1, c1) == (7, 0):
                castling_dict[color][1] = False
            if (r1, c1) == (7, 7):
                castling_dict[color][0] = False
        else:
            if (r1, c1) == (0, 0):
                castling_dict[color][1] = False
            if (r1, c1) == (0, 7):
                castling_dict[color][0] = False

    return new_enp, castling_dict

########################################
# Checkmate detection
########################################

def is_checkmate(board, color, castling_rights, en_passant_target):
    """
    Return True if 'color' is in check and has no legal moves => checkmate.
    """
    if not in_check(board, color):
        return False  # Not in check => can't be checkmate

    if not has_legal_move(board, color, castling_rights, en_passant_target):
        return True
    return False

########################################
# Stalemate detection
########################################

def is_stalemate(board, color, castling_rights, en_passant_target):
    """
    Return True if 'color' is NOT in check and has no legal moves => stalemate.
    """
    if in_check(board, color):
        return False  # In check => can't be stalemate

    if not has_legal_move(board, color, castling_rights, en_passant_target):
        return True
    return False

########################################
# Helper: has_legal_move
########################################

def has_legal_move(board, color, castling_rights, en_passant_target):
    """
    True if 'color' can make at least one legal move.
    We try every piece for 'color' and every possible destination.
    If any move is valid and doesn't leave us in check, we return True.
    """
    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if piece != '.' and get_piece_color(piece) == color:
                for rr in range(8):
                    for cc in range(8):
                        if is_valid_move(
                            board, (r, c), (rr, cc),
                            color == "white",
                            en_passant_target,
                            castling_rights,
                            checking_check=True
                        ):
                            # Attempt the move, see if we end up not in check
                            temp_board = copy_board(board)
                            temp_cr = {
                                "white": castling_rights["white"][:],
                                "black": castling_rights["black"][:]
                            }
                            _temp_enp, temp_cr = move_with_extras(
                                temp_board, (r, c), (rr, cc),
                                color == "white",
                                en_passant_target, temp_cr
                            )
                            if not in_check(temp_board, color):
                                return True
    return False

########################################
# Main loop
########################################

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
        player_color = 'white' if turn_white else 'black'
        player_str = 'White' if turn_white else 'Black'

        # Check checkmate first
        if is_checkmate(board, player_color, castling_rights, en_passant_target):
            # The *other* color is the winner (the color that just moved).
            winner = 'Black' if turn_white else 'White'
            print(f"Checkmate! {winner} wins!")
            sys.exit()

        # Then check stalemate
        if is_stalemate(board, player_color, castling_rights, en_passant_target):
            print("Stalemate! It's a draw.")
            sys.exit()

        # If not checkmate or stalemate but in check, warn
        if in_check(board, player_color):
            print(f"{player_str} is in check!")

        move_input = input(f"{player_str}'s move (e.g. 'e2 e4', or 'quit'): ")
        if move_input.lower() == 'quit':
            print("Goodbye.")
            sys.exit()

        start, end = parse_move(move_input)
        if start is None or end is None:
            print("Invalid format. Try 'e2 e4'.")
            continue

        # Validate
        if is_valid_move(board, start, end, turn_white, en_passant_target, castling_rights):
            # Double-check it doesn't leave king in check
            temp_board = copy_board(board)
            temp_cr = {
                "white": castling_rights["white"][:],
                "black": castling_rights["black"][:]
            }
            _temp_enp, temp_cr = move_with_extras(
                temp_board, start, end, turn_white,
                en_passant_target, temp_cr
            )
            if in_check(temp_board, player_color):
                print("Illegal: king would remain in check.")
                continue

            # Otherwise commit
            en_passant_target, castling_rights = move_with_extras(
                board, start, end, turn_white,
                en_passant_target, castling_rights
            )
            turn_white = not turn_white
        else:
            print("Illegal move. Try again.")

if __name__ == "__main__":
    main()
