"""
Chess Game Implementation

This module implements a complete chess game with all standard rules including:
- Basic piece movements
- Castling (kingside and queenside)
- En passant captures
- Pawn promotion
- Check and checkmate detection
- Stalemate detection

The board is represented as a 2D list of characters where:
- Uppercase letters represent white pieces (K,Q,R,B,N,P)
- Lowercase letters represent black pieces (k,q,r,b,n,p)
- Dots (.) represent empty squares
- Board coordinates follow standard chess notation (a1 to h8)

Usage:
    Run this file directly to start a game:
    $ python chess.py
    
    Enter moves in the format: 'e2 e4' (source square, space, target square)
    Enter 'quit' to end the game
"""

import sys

########################################
# Precompute piece moves (truth tables)
########################################

def in_bounds(r, c):
    """Check if a position (r,c) is within the 8x8 board boundaries."""
    return 0 <= r < 8 and 0 <= c < 8

def build_knight_moves():
    """
    Precompute all possible knight moves for each square.
    Returns a dict mapping (row,col) -> list of valid destination (row,col) tuples.
    """
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
    """
    Precompute all possible king moves for each square.
    Returns a dict mapping (row,col) -> list of valid destination (row,col) tuples.
    Does not include castling which is handled separately.
    """
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
    """
    Precompute all possible sliding piece moves (rooks and bishops).
    For each square, stores the list of squares that can be reached along each direction.
    Returns (rook_slides, bishop_slides) where each is a dict mapping
    (row,col) -> list of rays, where each ray is a list of (row,col) tuples.
    """
    rook_dirs = [(1,0), (-1,0), (0,1), (0,-1)]  # Vertical and horizontal
    bishop_dirs = [(1,1), (1,-1), (-1,1), (-1,-1)]  # Diagonals
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

# Precomputed move tables - computed once at module load time
KNIGHT_MOVES = build_knight_moves()
KING_MOVES   = build_king_moves()
ROOK_SLIDES, BISHOP_SLIDES = build_sliding_moves()

########################################
# Board setup + utilities
########################################

STARTING_BOARD = [
    list("rnbqkbnr"),  # Black pieces
    list("pppppppp"),  # Black pawns
    list("........"),  # Empty squares
    list("........"),
    list("........"),
    list("........"),
    list("PPPPPPPP"),  # White pawns
    list("RNBQKBNR"),  # White pieces
]

# Track castling rights for each color: [kingside, queenside]
CASTLE_RIGHTS = {
    "white": [True, True],
    "black": [True, True]
}

def copy_board(board):
    """Create a deep copy of the board state."""
    return [row[:] for row in board]

def get_piece_color(piece):
    """
    Returns the color of a piece or None if square is empty.
    piece: Single character representing the piece ('K','k','Q', etc)
    """
    if piece == ".":
        return None
    return "white" if piece.isupper() else "black"

def is_white(piece):
    """Returns True if piece is white (uppercase)."""
    return piece.isupper()

def is_black(piece):
    """Returns True if piece is black (lowercase)."""
    return piece.islower()

def print_board(board):
    """
    Print the current board state with rank and file labels.
    Uses chess notation: a-h for files (columns), 1-8 for ranks (rows).
    """
    print("  a b c d e f g h")
    for i in range(8):
        row_str = str(8 - i) + " "
        for j in range(8):
            row_str += board[i][j] + " "
        print(row_str + str(8 - i))
    print("  a b c d e f g h")

def parse_move(move_str):
    """
    Convert a move string (e.g. 'e2 e4') to board coordinates.
    Returns tuple of ((start_row, start_col), (end_row, end_col)) or (None, None) if invalid.
    """
    try:
        start_str, end_str = move_str.split()
        # Convert file (a-h) to column (0-7)
        c1 = ord(start_str[0].lower()) - ord('a')
        # Convert rank (1-8) to row (7-0)
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
    """
    Find the position of the king of given color.
    Returns (row, col) tuple or None if not found.
    """
    king_char = 'K' if color == 'white' else 'k'
    for r in range(8):
        for c in range(8):
            if board[r][c] == king_char:
                return (r, c)
    return None

def square_attacked_by(board, r, c, color):
    """
    Returns True if any piece of 'color' can legally move to square (r,c).
    Used for check detection and castling validation.
    """
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece != '.' and get_piece_color(piece) == color:
                if is_valid_move(
                    board, (row, col), (r, c),
                    color == "white", 
                    en_passant_target=None,
                    castling_rights=None,
                    checking_check=False  # Prevent infinite recursion
                ):
                    return True
    return False

def in_check(board, color):
    """
    Returns True if the king of 'color' is in check.
    A king is in check if it can be captured by any enemy piece.
    """
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
    """
    Check if a move from start to end is legal.
    
    Parameters:
    - board: Current board state
    - start: (row, col) tuple for starting square
    - end: (row, col) tuple for ending square
    - turn_white: True if it's white's turn
    - en_passant_target: Square that can be captured via en passant, or None
    - castling_rights: Dict tracking castling availability
    - checking_check: If True, verify move doesn't leave king in check
    
    Returns: True if move is legal
    """
    r1, c1 = start
    r2, c2 = end

    # Basic bounds checking
    if not in_bounds(r1, c1) or not in_bounds(r2, c2):
        return False

    piece = board[r1][c1]
    if piece == '.':
        return False

    # Verify correct color is moving
    piece_color = "white" if is_white(piece) else "black"
    if turn_white and piece_color != "white":
        return False
    if (not turn_white) and piece_color != "black":
        return False

    target = board[r2][c2]
    # Can't capture your own piece
    if target != '.' and get_piece_color(target) == piece_color:
        return False

    # Check piece-specific move rules
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

    # Verify move doesn't leave/put own king in check
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
    """
    Validate a pawn move according to chess rules:
    - Can move forward one square if target is empty
    - Can move forward two squares from starting position if path is clear
    - Can capture diagonally
    - Can capture en passant
    """
    r1, c1 = start
    r2, c2 = end
    piece = board[r1][c1]
    direction = -1 if turn_white else 1  # White moves up (-1), black moves down (+1)
    start_row = 6 if turn_white else 1   # Starting row for pawns
    enemy_color = 'black' if turn_white else 'white'

    # Single-step forward
    if c1 == c2 and (r2 == r1 + direction) and board[r2][c2] == '.':
        return True

    # Double-step from starting position
    if c1 == c2 and r1 == start_row and r2 == r1 + 2*direction:
        mid_r = r1 + direction
        if board[mid_r][c1] == '.' and board[r2][c2] == '.':
            return True

    # Diagonal capture or en passant
    if abs(c2 - c1) == 1 and r2 == r1 + direction:
        # Normal diagonal capture
        if board[r2][c2] != '.' and get_piece_color(board[r2][c2]) == enemy_color:
            return True
        # En passant capture
        if en_passant_target is not None:
            if (r2, c2) == en_passant_target and board[r2][c2] == '.':
                return True

    return False

def valid_rook_move(board, start, end):
    """
    Validate a rook move using precomputed sliding moves.
    Checks if target is reachable along any ray and path is clear.
    """
    for ray in ROOK_SLIDES[start]:
        if end in ray:
            for sq in ray:
                if sq == end:
                    return True
                if board[sq[0]][sq[1]] != '.':
                    return False
    return False

def valid_bishop_move(board, start, end):
    """
    Validate a bishop move using precomputed sliding moves.
    Checks if target is reachable along any ray and path is clear.
    """
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
    Validate a queen move by checking both rook and bishop patterns.
    A queen combines the movement capabilities of a rook and bishop.
    """
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
    
    Parameters:
    - color: 'white' or 'black'
    - side: 'king' or 'queen' (kingside or queenside castling)
    - castling_rights: Dict tracking if castling is still available
    
    Requirements for castling:
    1. King and rook haven't moved (tracked in castling_rights)
    2. No pieces between king and rook
    3. King is not in check
    4. King doesn't pass through check
    """
    row = 7 if color == 'white' else 0
    king_char = 'K' if color == 'white' else 'k'
    
    if side == 'king':
        if not castling_rights[0]:  # Lost castling rights
            return False
        if board[row][4] != king_char:  # King not in correct position
            return False
        if board[row][5] != '.' or board[row][6] != '.':  # Path not clear
            return False
        if not (board[row][7] in ('R','r') and get_piece_color(board[row][7]) == color):
            return False
        opponent = 'black' if color == 'white' else 'white'
        # Check if king is in check or passes through check
        if in_check(board, color):
            return False
        if square_attacked_by(board, row, 5, opponent):
            return False
        if square_attacked_by(board, row, 6, opponent):
            return False
        return True
    else:  # queen-side
        if not castling_rights[1]:  # Lost castling rights
            return False
        if board[row][4] != king_char:  # King not in correct position
            return False
        if board[row][3] != '.' or board[row][2] != '.' or board[row][1] != '.':  # Path not clear
            return False
        if not (board[row][0] in ('R','r') and get_piece_color(board[row][0]) == color):
            return False
        opponent = 'black' if color == 'white' else 'white'
        # Check if king is in check or passes through check
        if in_check(board, color):
            return False
        if square_attacked_by(board, row, 3, opponent):
            return False
        if square_attacked_by(board, row, 2, opponent):
            return False
        return True

def do_castle(board, color, side):
    """
    Execute a castling move by moving both king and rook.
    Assumes the move has already been validated.
    """
    row = 7 if color == 'white' else 0
    king_char = 'K' if color == 'white' else 'k'
    if side == 'king':
        # Move king from e1 to g1 (or e8 to g8)
        board[row][4] = '.'
        board[row][6] = king_char
        # Move rook from h1 to f1 (or h8 to f8)
        board[row][5] = board[row][7]
        board[row][7] = '.'
    else:
        # Move king from e1 to c1 (or e8 to c8)
        board[row][4] = '.'
        board[row][2] = king_char
        # Move rook from a1 to d1 (or a8 to d8)
        board[row][3] = board[row][0]
        board[row][0] = '.'

def promotion_choice(color):
    """
    Handle pawn promotion by getting user input.
    Returns the character representing the chosen piece.
    """
    while True:
        choice = input(f"Promote to Q, R, B, or N? ").strip().upper()
        if choice in ['Q','R','B','N']:
            return choice if color == 'white' else choice.lower()
        print("Invalid choice, try Q, R, B, or N.")

########################################
# Move execution
########################################

def move_with_extras(board, start, end, turn_white, en_passant_target, castling_dict):
    """
    Execute a move and handle special cases (castling, en passant, promotion).
    Updates the board in place and returns (new_en_passant_target, updated_castling_rights).
    
    This function assumes the move has already been validated as legal.
    """
    r1, c1 = start
    r2, c2 = end
    piece = board[r1][c1]
    p = piece.upper()
    color = 'white' if is_white(piece) else 'black'
    row = 7 if color == 'white' else 0

    new_enp = None

    # Handle castling
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
    
    # Handle en passant capture
    if p == 'P' and en_passant_target is not None:
        ep_r, ep_c = en_passant_target
        if (r2, c2) == (ep_r, ep_c) and c1 != c2 and board[r2][c2] == '.':
            board[r1][c2] = '.'  # remove captured pawn

    board[r2][c2] = piece

    # Set up new en passant target if pawn moves two squares
    if p == 'P':
        direction = -1 if color=='white' else 1
        if abs(r2 - r1) == 2:
            mid_r = (r1 + r2) // 2
            new_enp = (mid_r, c1)

    # Handle pawn promotion
    if p == 'P':
        if color == 'white' and r2 == 0:
            board[r2][c2] = promotion_choice(color)
        elif color == 'black' and r2 == 7:
            board[r2][c2] = promotion_choice(color)

    # Update castling rights if king or rook moves
    if p == 'K':
        castling_dict[color] = [False, False]
    elif p == 'R':
        if color=='white':
            if (r1, c1) == (7, 0):
                castling_dict[color][1] = False  # Lost queenside
            if (r1, c1) == (7, 7):
                castling_dict[color][0] = False  # Lost kingside
        else:
            if (r1, c1) == (0, 0):
                castling_dict[color][1] = False  # Lost queenside
            if (r1, c1) == (0, 7):
                castling_dict[color][0] = False  # Lost kingside

    return new_enp, castling_dict

########################################
# Checkmate detection
########################################

def is_checkmate(board, color, castling_rights, en_passant_target):
    """
    Check if the given color is in checkmate.
    A player is in checkmate if they are in check and have no legal moves.
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
    Check if the given color is in stalemate.
    A player is in stalemate if they are NOT in check but have no legal moves.
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
    Check if the given color has at least one legal move available.
    Used by both checkmate and stalemate detection.
    
    Approach:
    1. Try every piece of the given color
    2. Try every possible destination square
    3. If any move is legal and doesn't leave king in check, return True
    4. If no legal moves found, return False
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
                            # Try the move and check if it leaves king in check
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
# Main game loop
########################################

def main():
    """
    Main game loop handling:
    1. Board setup and initialization
    2. Turn alternation
    3. Move input and validation
    4. Game end conditions (checkmate, stalemate)
    """
    # Initialize game state
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

        # Check game-ending conditions
        if is_checkmate(board, player_color, castling_rights, en_passant_target):
            winner = 'Black' if turn_white else 'White'
            print(f"Checkmate! {winner} wins!")
            sys.exit()

        if is_stalemate(board, player_color, castling_rights, en_passant_target):
            print("Stalemate! It's a draw.")
            sys.exit()

        # Warn if in check
        if in_check(board, player_color):
            print(f"{player_str} is in check!")

        # Get and validate move
        move_input = input(f"{player_str}'s move (e.g. 'e2 e4', or 'quit'): ")
        if move_input.lower() == 'quit':
            print("Goodbye.")
            sys.exit()

        start, end = parse_move(move_input)
        if start is None or end is None:
            print("Invalid format. Try 'e2 e4'.")
            continue

        # Validate move
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

            # Execute move
            en_passant_target, castling_rights = move_with_extras(
                board, start, end, turn_white,
                en_passant_target, castling_rights
            )
            turn_white = not turn_white
        else:
            print("Illegal move. Try again.")

if __name__ == "__main__":
    main()
