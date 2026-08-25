#include <pybind11/pybind11.h>

#include <oneapi/tbb/blocked_range.h>
#include <oneapi/tbb/parallel_reduce.h>
#include <oneapi/tbb/task_arena.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>

namespace py = pybind11;

namespace {

constexpr std::uint32_t PHILOX_M0 = 0xD2511F53U;
constexpr std::uint32_t PHILOX_M1 = 0xCD9E8D57U;
constexpr std::uint32_t PHILOX_W0 = 0x9E3779B9U;
constexpr std::uint32_t PHILOX_W1 = 0xBB67AE85U;

struct Counter4 {
    std::uint32_t x0;
    std::uint32_t x1;
    std::uint32_t x2;
    std::uint32_t x3;
};

inline Counter4 philox_round(Counter4 value, std::uint32_t key0, std::uint32_t key1) noexcept {
    const std::uint64_t product0 = static_cast<std::uint64_t>(PHILOX_M0) * value.x0;
    const std::uint64_t product1 = static_cast<std::uint64_t>(PHILOX_M1) * value.x2;
    return {
        static_cast<std::uint32_t>(product1 >> 32U) ^ value.x1 ^ key0,
        static_cast<std::uint32_t>(product1),
        static_cast<std::uint32_t>(product0 >> 32U) ^ value.x3 ^ key1,
        static_cast<std::uint32_t>(product0),
    };
}

inline Counter4 philox4x32x10(
    const std::uint64_t counter,
    const std::uint64_t subsequence,
    const std::uint64_t seed) noexcept {
    Counter4 value{
        static_cast<std::uint32_t>(counter),
        static_cast<std::uint32_t>(counter >> 32U),
        static_cast<std::uint32_t>(subsequence),
        static_cast<std::uint32_t>(subsequence >> 32U),
    };
    std::uint32_t key0 = static_cast<std::uint32_t>(seed);
    std::uint32_t key1 = static_cast<std::uint32_t>(seed >> 32U);
    for (int round = 0; round < 10; ++round) {
        value = philox_round(value, key0, key1);
        key0 += PHILOX_W0;
        key1 += PHILOX_W1;
    }
    return value;
}

struct Totals {
    std::uint64_t errors = 0;
    std::uint64_t bits = 0;

    Totals& operator+=(const Totals& other) noexcept {
        errors += other.errors;
        bits += other.bits;
        return *this;
    }
};

Totals run_uncoded_range(
    const oneapi::tbb::blocked_range<std::uint64_t>& range,
    const std::uint64_t groups_per_trial,
    const std::uint64_t bit_length,
    const std::uint64_t trial_start,
    const std::uint64_t source_seed,
    const std::uint64_t noise_seed,
    const std::uint64_t error_threshold) {
    (void)source_seed;  // BER after uncoded hard BPSK depends only on decision errors.
    Totals totals;
    for (std::uint64_t flat = range.begin(); flat != range.end(); ++flat) {
        const std::uint64_t local_trial = flat / groups_per_trial;
        const std::uint64_t group = flat - local_trial * groups_per_trial;
        const std::uint64_t trial = trial_start + local_trial;
        const Counter4 noise_random = philox4x32x10(group, trial, noise_seed);
        const std::array<std::uint32_t, 4> noises{noise_random.x0, noise_random.x1, noise_random.x2, noise_random.x3};
        const std::uint64_t valid = std::min<std::uint64_t>(4U, bit_length - group * 4U);
        for (std::uint64_t lane = 0; lane < valid; ++lane) {
            totals.errors += noises[static_cast<std::size_t>(lane)] < error_threshold;
        }
        totals.bits += valid;
    }
    return totals;
}

Totals run_hamming_range(
    const oneapi::tbb::blocked_range<std::uint64_t>& range,
    const std::uint64_t groups_per_trial,
    const std::uint64_t trial_start,
    const std::uint64_t source_seed,
    const std::uint64_t noise_seed,
    const std::uint64_t error_threshold) {
    static constexpr std::array<std::int8_t, 8> ERROR_INDEX{-1, 4, 5, 0, 6, 1, 2, 3};
    Totals totals;
    for (std::uint64_t flat = range.begin(); flat != range.end(); ++flat) {
        const std::uint64_t local_trial = flat / groups_per_trial;
        const std::uint64_t group = flat - local_trial * groups_per_trial;
        const std::uint64_t trial = trial_start + local_trial;
        std::array<std::uint8_t, 7> received{};
        std::array<std::uint8_t, 4> data{};
        const Counter4 source_random = philox4x32x10(group, trial, source_seed);
        data[0] = static_cast<std::uint8_t>(source_random.x0 & 1U);
        data[1] = static_cast<std::uint8_t>(source_random.x1 & 1U);
        data[2] = static_cast<std::uint8_t>(source_random.x2 & 1U);
        data[3] = static_cast<std::uint8_t>(source_random.x3 & 1U);
        std::copy(data.begin(), data.end(), received.begin());
        received[4] = data[0] ^ data[1] ^ data[3];
        received[5] = data[0] ^ data[2] ^ data[3];
        received[6] = data[1] ^ data[2] ^ data[3];
        const std::uint64_t coded_start = group * 7U;
        std::uint64_t cached_counter = std::numeric_limits<std::uint64_t>::max();
        Counter4 noise_random{};
        for (std::uint64_t index = 0; index < 7U; ++index) {
            const std::uint64_t coded_index = coded_start + index;
            const std::uint64_t counter = coded_index >> 2U;
            if (counter != cached_counter) {
                noise_random = philox4x32x10(counter, trial, noise_seed);
                cached_counter = counter;
            }
            const std::array<std::uint32_t, 4> lanes{noise_random.x0, noise_random.x1, noise_random.x2, noise_random.x3};
            received[index] ^= static_cast<std::uint8_t>(lanes[static_cast<std::size_t>(coded_index & 3U)] < error_threshold);
        }
        const std::uint8_t s1 = received[0] ^ received[1] ^ received[3] ^ received[4];
        const std::uint8_t s2 = received[0] ^ received[2] ^ received[3] ^ received[5];
        const std::uint8_t s3 = received[1] ^ received[2] ^ received[3] ^ received[6];
        const std::uint8_t syndrome = s1 + 2U * s2 + 4U * s3;
        if (syndrome != 0U) {
            received[static_cast<std::size_t>(ERROR_INDEX[syndrome])] ^= 1U;
        }
        for (std::size_t index = 0; index < 4U; ++index) {
            totals.errors += received[index] != data[index];
        }
        totals.bits += 4U;
    }
    return totals;
}

Totals run_repetition_range(
    const oneapi::tbb::blocked_range<std::uint64_t>& range,
    const std::uint64_t groups_per_trial,
    const std::uint64_t bit_length,
    const std::uint64_t trial_start,
    const std::uint64_t noise_seed,
    const std::uint64_t error_threshold) {
    Totals totals;
    for (std::uint64_t flat = range.begin(); flat != range.end(); ++flat) {
        const std::uint64_t local_trial = flat / groups_per_trial;
        const std::uint64_t group = flat - local_trial * groups_per_trial;
        const std::uint64_t trial = trial_start + local_trial;
        const std::uint64_t coded_counter = group * 3U;
        const std::array<Counter4, 3> random{
            philox4x32x10(coded_counter, trial, noise_seed),
            philox4x32x10(coded_counter + 1U, trial, noise_seed),
            philox4x32x10(coded_counter + 2U, trial, noise_seed),
        };
        const std::array<std::uint32_t, 12> lanes{
            random[0].x0, random[0].x1, random[0].x2, random[0].x3,
            random[1].x0, random[1].x1, random[1].x2, random[1].x3,
            random[2].x0, random[2].x1, random[2].x2, random[2].x3,
        };
        const std::uint64_t valid = std::min<std::uint64_t>(4U, bit_length - group * 4U);
        for (std::uint64_t bit = 0; bit < valid; ++bit) {
            const std::size_t offset = static_cast<std::size_t>(bit * 3U);
            const int flips = static_cast<int>(lanes[offset] < error_threshold)
                + static_cast<int>(lanes[offset + 1U] < error_threshold)
                + static_cast<int>(lanes[offset + 2U] < error_threshold);
            totals.errors += flips >= 2;
        }
        totals.bits += valid;
    }
    return totals;
}

py::dict run_bpsk_awgn_batch(
    const std::uint64_t bit_length,
    const std::uint64_t trial_start,
    const std::uint64_t trial_count,
    const double snr_db,
    const std::uint64_t source_seed,
    const std::uint64_t noise_seed,
    const int workers,
    const int coding) {
    if (bit_length == 0U || trial_count == 0U) {
        throw std::invalid_argument("bit_length and trial_count must be positive");
    }
    if (coding < 0 || coding > 2) {
        throw std::invalid_argument("coding must be 0 (none), 1 (Hamming 7,4), or 2 (Repetition-3)");
    }
    if (coding == 1 && bit_length % 4U != 0U) {
        throw std::invalid_argument("Hamming (7,4) native execution requires bit_length divisible by 4");
    }
    if (!std::isfinite(snr_db)) {
        throw std::invalid_argument("snr_db must be finite");
    }
    const int concurrency = std::max(1, workers);
    const double error_probability = 0.5 * std::erfc(std::sqrt(std::pow(10.0, snr_db / 10.0)));
    const std::uint64_t error_threshold = static_cast<std::uint64_t>(
        std::clamp(error_probability, 0.0, 1.0) * 4294967296.0);
    Totals totals;
    {
        py::gil_scoped_release release;
        oneapi::tbb::task_arena arena(concurrency);
        totals = arena.execute([&] {
            if (coding == 1) {
                const std::uint64_t groups = bit_length / 4U;
                const std::uint64_t total_groups = groups * trial_count;
                return oneapi::tbb::parallel_reduce(
                    oneapi::tbb::blocked_range<std::uint64_t>(0U, total_groups, 8192U),
                    Totals{},
                    [&](const auto& range, Totals local) {
                        local += run_hamming_range(range, groups, trial_start, source_seed, noise_seed, error_threshold);
                        return local;
                    },
                    [](Totals left, const Totals& right) {
                        left += right;
                        return left;
                    });
            }
            if (coding == 2) {
                const std::uint64_t groups = (bit_length + 3U) / 4U;
                const std::uint64_t total_groups = groups * trial_count;
                return oneapi::tbb::parallel_reduce(
                    oneapi::tbb::blocked_range<std::uint64_t>(0U, total_groups, 4096U),
                    Totals{},
                    [&](const auto& range, Totals local) {
                        local += run_repetition_range(range, groups, bit_length, trial_start, noise_seed, error_threshold);
                        return local;
                    },
                    [](Totals left, const Totals& right) {
                        left += right;
                        return left;
                    });
            }
            const std::uint64_t groups = (bit_length + 3U) / 4U;
            const std::uint64_t total_groups = groups * trial_count;
            return oneapi::tbb::parallel_reduce(
                oneapi::tbb::blocked_range<std::uint64_t>(0U, total_groups, 4096U),
                Totals{},
                [&](const auto& range, Totals local) {
                    local += run_uncoded_range(range, groups, bit_length, trial_start, source_seed, noise_seed, error_threshold);
                    return local;
                },
                [](Totals left, const Totals& right) {
                    left += right;
                    return left;
                });
        });
    }
    py::dict result;
    result["bit_errors"] = totals.errors;
    result["total_bits"] = totals.bits;
    result["completed_trials"] = trial_count;
    return result;
}

}  // namespace

PYBIND11_MODULE(_native_core, module) {
    module.doc() = "SignalLab fused single-machine Monte-Carlo kernels";
    module.attr("__version__") = "0.1.0";
    module.def(
        "run_bpsk_awgn_batch",
        &run_bpsk_awgn_batch,
        py::arg("bit_length"),
        py::arg("trial_start"),
        py::arg("trial_count"),
        py::arg("snr_db"),
        py::arg("source_seed"),
        py::arg("noise_seed"),
        py::arg("workers"),
        py::arg("coding"),
        "Run a fused BPSK/AWGN/BER batch with no code, Hamming (7,4), or Repetition-3.");
}
