#pragma once
#include <vector>
#include "move.h"

class Board {
public:
    // Pieces encoding:
    // 0 empty
    // 1 my man
    // 2 my king
    // 3 opp man
    // 4 opp king
    Board(int width, int height, std::vector<std::vector<int>> grid)
        : width_(width), height_(height), grid_(std::move(grid)) {}

    int pieceIn(int col, int row) const;
    void placePiece(int col, int row, int value);

    int getWidth() const { return width_; }
    int getHeight() const { return height_; }

    // Generate legal moves for each side (needed for minimax)
    std::vector<Move> generateMovesMy() const;
    std::vector<Move> generateMovesOpp() const;

    // Apply a move -> returns the resulting board (pure functional, ideal for minimax)
    Board applyMoveMy(const Move& m) const;
    Board applyMoveOpp(const Move& m) const;

    // Board evaluation (positive = good for "my" side)
    int evaluate() const;

private:
    int width_;
    int height_;
    std::vector<std::vector<int>> grid_;

    bool inBounds(int c, int r) const;
    bool isMyPiece(int p) const { return p == 1 || p == 2; }
    bool isOppPiece(int p) const { return p == 3 || p == 4; }
    bool isKing(int p) const { return p == 2 || p == 4; }

    // Helpers to build moves
    std::vector<Move> genCapturesFrom(int c, int r, bool mySide) const;
    void dfsCaptures(Board b, int c, int r, bool mySide,
                     std::vector<std::pair<int,int>> path,
                     std::vector<Move>& out) const;

    std::vector<Move> genQuietFrom(int c, int r, bool mySide) const;

    // Internal apply (mySide decides direction & promotion)
    Board applyMoveInternal(const Move& m, bool mySide) const;
};
