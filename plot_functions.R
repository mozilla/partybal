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

plot_mean <- function(df, metric, comparison) {
    df <- filter(df, metric == !!metric, statistic == "mean")
    if(comparison == "none") {
        df <- filter(df, is.na(comparison))
        g <- ggplot(df, aes(window_index, point, ymin=lower, ymax=upper, group=branch)) +
            geom_line(aes(color=branch)) +
            geom_ribbon(aes(fill=branch), alpha=0.3) +
            labs(title=metric, x="Quantile")
    } else {
        df <- filter(df, comparison == !!comparison)
        g <- ggplot(df, aes(window_index, point, ymin=lower, ymax=upper, group=0)) +
            geom_line(aes(color=branch)) +
            geom_ribbon(alpha=0.3) +
            labs(title=paste0(metric, " (", comparison, ")"), x="Quantile")
    }
    g
}

plot_binomial <- function(...) { }

plot_count <- function(...) { }