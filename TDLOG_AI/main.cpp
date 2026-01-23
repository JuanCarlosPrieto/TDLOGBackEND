#include <iostream>
#include <vector>
#include <utility>
#include "httplib.h"
#include "json.hpp"

#include "board.h"
#include "move.h"
#include "search.h"

using json = nlohmann::json;

static Move jsonToMove(const json& j) {
    std::vector<std::pair<int,int>> path;
    for (const auto& p : j.at("path")) {
        path.push_back({p.at(0).get<int>(), p.at(1).get<int>()});
    }
    return Move(std::move(path));
}

static json moveToJson(const Move& m) {
    json out;
    out["path"] = json::array();
    for (auto [c, r] : m.path()) {
        out["path"].push_back({c, r});
    }
    return out;
}

static Board boardFromJson(const json& j) {
    auto gridJson = j.at("grid");
    int h = (int)gridJson.size();
    int w = (h > 0) ? (int)gridJson.at(0).size() : 0;

    std::vector<std::vector<int>> grid(h, std::vector<int>(w, 0));
    for (int r = 0; r < h; ++r) {
        for (int c = 0; c < w; ++c) {
            grid[r][c] = gridJson[r][c].get<int>();
        }
    }
    return Board(w, h, std::move(grid));
}

int main() {
    httplib::Server server;

    server.Get("/health", [](const httplib::Request&, httplib::Response& res) {
        res.set_content(R"({"ok":true})", "application/json");
    });

    server.Post("/ai/move", [](const httplib::Request& req, httplib::Response& res) {
        try {
            json j = json::parse(req.body);

            Board b = boardFromJson(j);

            int depth = 6;
            if (j.contains("depth")) depth = j["depth"].get<int>();

            // Si recibes turn y a veces no es tu turno, puedes:
            // - o rechazar
            // - o calcular para el lado correspondiente
            // Aquí asumimos que SIEMPRE llaman cuando es turno de "my"
            AlphaBeta search(depth);
            SearchResult sr = search.findBestMove(b);

            json out;
            out["score"] = sr.score;
            out.update(moveToJson(sr.bestMove));

            res.set_content(out.dump(), "application/json");
        } catch (const std::exception& e) {
            json err;
            err["error"] = std::string("bad_request: ") + e.what();
            res.status = 400;
            res.set_content(err.dump(), "application/json");
        }
    });

    std::cout << "AI engine listening on http://localhost:8080\n";
    server.listen("localhost", 8080);
    return 0;
}
