#include "board.h"
#include <algorithm>

// -------------------- basics --------------------
bool Board::inBounds(int c, int r) const {
    return c >= 0 && c < width_ && r >= 0 && r < height_;
}

int Board::pieceIn(int col, int row) const {
    if (!inBounds(col, row)) return -1;
    return grid_[row][col];
}

void Board::placePiece(int col, int row, int value) {
    if (inBounds(col, row)) grid_[row][col] = value;
}

// -------------------- move generation entrypoints --------------------
std::vector<Move> Board::generateMovesMy() const {
    std::vector<Move> captures, quiet;

    for (int r = 0; r < height_; ++r) {
        for (int c = 0; c < width_; ++c) {
            int p = pieceIn(c, r);
            if (!isMyPiece(p)) continue;

            auto cap = genCapturesFrom(c, r, /*mySide=*/true);
            captures.insert(captures.end(), cap.begin(), cap.end());
        }
    }

    // capture is mandatory
    if (!captures.empty()) return captures;

    for (int r = 0; r < height_; ++r) {
        for (int c = 0; c < width_; ++c) {
            int p = pieceIn(c, r);
            if (!isMyPiece(p)) continue;

            auto q = genQuietFrom(c, r, /*mySide=*/true);
            quiet.insert(quiet.end(), q.begin(), q.end());
        }
    }
    return quiet;
}

std::vector<Move> Board::generateMovesOpp() const {
    std::vector<Move> captures, quiet;

    for (int r = 0; r < height_; ++r) {
        for (int c = 0; c < width_; ++c) {
            int p = pieceIn(c, r);
            if (!isOppPiece(p)) continue;

            auto cap = genCapturesFrom(c, r, /*mySide=*/false);
            captures.insert(captures.end(), cap.begin(), cap.end());
        }
    }

    if (!captures.empty()) return captures;

    for (int r = 0; r < height_; ++r) {
        for (int c = 0; c < width_; ++c) {
            int p = pieceIn(c, r);
            if (!isOppPiece(p)) continue;

            auto q = genQuietFrom(c, r, /*mySide=*/false);
            quiet.insert(quiet.end(), q.begin(), q.end());
        }
    }
    return quiet;
}

// -------------------- capture generation --------------------
std::vector<Move> Board::genCapturesFrom(int c, int r, bool mySide) const {
    std::vector<Move> out;
    std::vector<std::pair<int,int>> path = {{c, r}};

    Board b = *this;
    dfsCaptures(b, c, r, mySide, path, out);

    // dfs pushes only completed capture sequences; but if no capture exists it returns empty
    return out;
}

void Board::dfsCaptures(Board b, int c, int r, bool mySide,
                        std::vector<std::pair<int,int>> path,
                        std::vector<Move>& out) const {

    const int piece = b.pieceIn(c, r);
    const bool king = b.isKing(piece);

    // Jump directions (2 steps)
    // For mySide: forward is +1 row; for opp: forward is -1 row
    const int fwd = mySide ? +1 : -1;

    std::vector<std::pair<int,int>> jumpDirs;
    // forward jumps always allowed
    jumpDirs.push_back({+2, +2*fwd});
    jumpDirs.push_back({-2, +2*fwd});
    // backward jumps only if king
    if (king) {
        jumpDirs.push_back({+2, -2*fwd});
        jumpDirs.push_back({-2, -2*fwd});
    }

    bool foundAny = false;

    for (auto [dc, dr] : jumpDirs) {
        int lc = c + dc;
        int lr = r + dr;
        int mc = c + dc/2;
        int mr = r + dr/2;

        if (!b.inBounds(lc, lr) || !b.inBounds(mc, mr)) continue;

        int mid = b.pieceIn(mc, mr);
        int land = b.pieceIn(lc, lr);

        bool midIsEnemy = mySide ? b.isOppPiece(mid) : b.isMyPiece(mid);
        if (midIsEnemy && land == 0) {
            foundAny = true;

            Board nb = b;
            // move piece
            nb.placePiece(c, r, 0);
            nb.placePiece(mc, mr, 0); // remove captured piece
            nb.placePiece(lc, lr, piece);

            auto npath = path;
            npath.push_back({lc, lr});

            // continue chaining
            dfsCaptures(nb, lc, lr, mySide, npath, out);
        }
    }

    // If we found at least one capture from this position, continuation happens above.
    // If we found none, and this path has length > 1, it means we completed a capture sequence.
    if (!foundAny && path.size() > 1) {
        out.emplace_back(path);
    }
}

// -------------------- quiet moves --------------------
std::vector<Move> Board::genQuietFrom(int c, int r, bool mySide) const {
    std::vector<Move> out;

    const int piece = pieceIn(c, r);
    const bool king = isKing(piece);
    const int fwd = mySide ? +1 : -1;

    std::vector<std::pair<int,int>> stepDirs;
    // forward steps
    stepDirs.push_back({+1, +1*fwd});
    stepDirs.push_back({-1, +1*fwd});
    // backward steps only if king
    if (king) {
        stepDirs.push_back({+1, -1*fwd});
        stepDirs.push_back({-1, -1*fwd});
    }

    for (auto [dc, dr] : stepDirs) {
        int nc = c + dc;
        int nr = r + dr;
        if (!inBounds(nc, nr)) continue;
        if (pieceIn(nc, nr) != 0) continue;

        out.emplace_back(std::vector<std::pair<int,int>>{{c, r}, {nc, nr}});
    }

    return out;
}

// -------------------- apply move --------------------
Board Board::applyMoveInternal(const Move& m, bool mySide) const {
    Board nb = *this;
    const auto& path = m.path();
    if (path.size() < 2) return nb;

    auto [sc, sr] = path.front();
    int piece = nb.pieceIn(sc, sr);

    nb.placePiece(sc, sr, 0);

    for (size_t i = 1; i < path.size(); ++i) {
        auto [pc, pr] = path[i-1];
        auto [cc, cr] = path[i];

        int dc = cc - pc;
        int dr = cr - pr;

        // capture if jump of 2
        if (std::abs(dc) == 2 && std::abs(dr) == 2) {
            int mc = pc + dc/2;
            int mr = pr + dr/2;
            nb.placePiece(mc, mr, 0);
        }
    }

    auto [ec, er] = path.back();

    // Promotion
    // My man reaches last row (height-1). Opp man reaches row 0.
    if (mySide && piece == 1 && er == nb.getHeight() - 1) piece = 2;
    if (!mySide && piece == 3 && er == 0) piece = 4;

    nb.placePiece(ec, er, piece);
    return nb;
}

Board Board::applyMoveMy(const Move& m) const {
    return applyMoveInternal(m, true);
}

Board Board::applyMoveOpp(const Move& m) const {
    return applyMoveInternal(m, false);
}

// -------------------- evaluation --------------------
int Board::evaluate() const {
    const int MAN = 100;
    const int KING = 180;
    const int MOB = 2;
    const int ADV = 1;
    const int CAP = 15;

    int myMen = 0, myKings = 0, opMen = 0, opKings = 0;
    int myAdvance = 0, opAdvance = 0;

    for (int r = 0; r < height_; ++r) {
        for (int c = 0; c < width_; ++c) {
            int p = pieceIn(c, r);
            if (p == 1) { myMen++;  myAdvance += r; }
            if (p == 2) { myKings++; }
            if (p == 3) { opMen++;  opAdvance += (height_ - 1 - r); }
            if (p == 4) { opKings++; }
        }
    }

    int material = MAN * (myMen - opMen) + KING * (myKings - opKings);
    int advance  = ADV * (myAdvance - opAdvance);

    // compute moves once
    auto movesMy  = generateMovesMy();
    auto movesOpp = generateMovesOpp();

    int mobility = MOB * ((int)movesMy.size() - (int)movesOpp.size());

    auto isCaptureMove = [](const Move& mv) {
        const auto& p = mv.path();
        if (p.size() < 2) return false;
        return std::abs(p[1].first - p[0].first) == 2; // jump
    };

    int myCaps = 0, opCaps = 0;
    for (const auto& mv : movesMy)  if (isCaptureMove(mv))  myCaps++;
    for (const auto& mv : movesOpp) if (isCaptureMove(mv)) opCaps++;

    int captures = CAP * (myCaps - opCaps);

    return material + advance + mobility + captures;
}
