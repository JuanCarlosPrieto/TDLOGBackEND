#pragma once
#include <utility>
#include <vector>

class Move {
public:
    Move() = default;
    explicit Move(std::vector<std::pair<int, int>> path)
        : path_(std::move(path)) {}

    const std::vector<std::pair<int, int>>& path() const { return path_; }

private:
    std::vector<std::pair<int, int>> path_;
};
