#pragma once
#include <limits>
#include <algorithm>
#include "board.h"
#include "move.h"

struct SearchResult {
    Move bestMove;
    int score = 0;
};

class AlphaBeta {
public:
    explicit AlphaBeta(int depth)
        : depth_(depth) {}

    SearchResult findBestMove(const Board& b) const {
        SearchResult res;
        auto moves = b.generateMovesMy();

        if (moves.empty()) {
            res.score = b.evaluate();
            res.bestMove = Move{};
            return res;
        }

        int alpha = std::numeric_limits<int>::min();
        int beta  = std::numeric_limits<int>::max();

        int bestScore = std::numeric_limits<int>::min();
        Move bestMove = moves.front(); // fallback seguro

        for (const auto& m : moves) {
            Board nb = b.applyMoveMy(m);
            int val = alphabeta(nb, depth_ - 1, alpha, beta, /*myTurn=*/false);

            if (val > bestScore) {
                bestScore = val;
                bestMove = m;
            }

            alpha = std::max(alpha, val);
            // (no es obligatorio cortar aquí, pero está bien)
        }

        res.score = bestScore;
        res.bestMove = bestMove;
        return res;
    }

private:
    int depth_;

    int alphabeta(const Board& b, int depth, int alpha, int beta, bool myTurn) const {
        if (depth <= 0) {
            return b.evaluate();
        }

        if (myTurn) {
            // MAX
            auto moves = b.generateMovesMy();
            if (moves.empty()) return b.evaluate();

            int best = std::numeric_limits<int>::min();

            for (const auto& m : moves) {
                Board nb = b.applyMoveMy(m);
                int val = alphabeta(nb, depth - 1, alpha, beta, /*myTurn=*/false);

                best = std::max(best, val);
                alpha = std::max(alpha, val);

                if (alpha >= beta) break; // poda
            }
            return best;
        } else {
            // MIN
            auto moves = b.generateMovesOpp();
            if (moves.empty()) return b.evaluate();

            int best = std::numeric_limits<int>::max();

            for (const auto& m : moves) {
                Board nb = b.applyMoveOpp(m);
                int val = alphabeta(nb, depth - 1, alpha, beta, /*myTurn=*/true);

                best = std::min(best, val);
                beta = std::min(beta, val);

                if (alpha >= beta) break; // poda
            }
            return best;
        }
    }
};
