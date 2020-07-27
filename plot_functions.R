integer_breaks = function(x) {
    if(x[2] - x[1] <= 6) {
        seq(ceiling(x[1]), floor(x[2]), by = 1)
    } else {
        pretty(x, n=6)
    }
}

plot_deciles <- function(df, metric, comparison) {
    df <- filter(df, metric == !!metric, statistic == "deciles")
    if(comparison == "none") {
        df <- filter(df, is.na(comparison))
        g <- ggplot(df, aes(parameter, point, ymin=lower, ymax=upper, group=branch)) +
            geom_line(aes(color=branch)) +
            geom_ribbon(aes(fill=branch), alpha=0.3) +
            labs(title=metric, x="Quantile") +
            facet_wrap(~window_index)
    } else {
        df <- filter(df, comparison == !!comparison)
        g <- ggplot(df, aes(parameter, point, ymin=lower, ymax=upper, group=0)) +
            geom_line(aes(color=branch)) +
            geom_ribbon(alpha=0.3) +
            labs(title=paste0(metric, " (", comparison, ")"), x="Quantile") +
            facet_wrap(~window_index)
    }
    g
}

plot_mean <- function(df, metric, comparison, statistic="mean") {
    df <- filter(df, metric == !!metric, statistic == !!statistic)
    if(comparison == "none") {
        df <- filter(df, is.na(comparison))
        g <- ggplot(df, aes(window_index, point, ymin=lower, ymax=upper, group=branch)) +
            geom_line(aes(color=branch)) +
            geom_ribbon(aes(fill=branch), alpha=0.3) +
            labs(title=metric, x="Window index") +
            scale_x_continuous(breaks=integer_breaks)
    } else {
        df <- filter(df, comparison == !!comparison)
        g <- ggplot(df, aes(window_index, point, ymin=lower, ymax=upper, group=0)) +
            geom_line(aes(color=branch)) +
            geom_ribbon(alpha=0.3) +
            labs(title=paste0(metric, " (", comparison, ")"), x="Window index") +
            scale_x_continuous(breaks=integer_breaks)
    }
    g
}

plot_binomial <- function(...) { plot_mean(..., "binomial") }

plot_count <- function(df, metric, comparison) {
    filter(df, metric == !!metric) %>%
        slice_min(window_index, n=1, with_ties=TRUE) %>%
        select(Branch=branch, Clients=point)
 }