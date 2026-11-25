%% MTR896 - Phase 3 results, 3D plots
%  Simulated QBER and key rate for an N-Charlie Qline chain over Montreal
%  fibre geography. Data produced by qline_chain.py (SquidASM/NetSquid).
%
%  Topology: linear chain, Alice - C1 - ... - CN - Bob.
%  Measured: end-to-end Alice<->Bob key pair.
%  Error bars are 1 standard error; 95% CI = +/- 2*se.
%
%  Runs in MATLAB and in GNU Octave (free). Octave needs:  pkg load statistics
%
%  Figures produced:
%    1  ribbon  - QBER curves at both spacings, in 3D
%    2  surf    - QBER surface over (node count, spacing)
%    3  bar3    - node ceiling by profile and spacing
%    4  plot3   - QBER / key-rate trajectory

clear; close all; clc;

%% ------------------------------------------------------------------ data
% advanced profile, 25 km spacing, 8000 pooled rounds/point
adv25.N    = 1:14;
adv25.qber = [1.79 2.56 3.69 5.07 5.23 5.90 7.14 7.43 8.03 9.03 ...
              9.94 10.64 11.59 11.71];
adv25.se   = [0.21 0.25 0.30 0.34 0.35 0.38 0.41 0.41 0.43 0.46 ...
              0.48 0.49 0.50 0.51];
adv25.rate = [61.5 50.8 45.7 42.7 40.4 38.3 37.7 38.2 36.7 35.1 ...
              33.9 34.2 34.1 33.8];

% advanced profile, 10 km spacing, 2000 rounds/point
adv10.N    = 1:11;
adv10.qber = [1.48 2.15 2.65 4.91 4.25 5.65 5.56 6.35 7.65 8.91 9.72];
adv10.se   = [0.38 0.45 0.50 0.70 0.63 0.72 0.73 0.76 0.85 0.91 0.94];
adv10.rate = [102 97.5 93.8 84.4 88.5 87.8 83.9 86.2 80.6 80.0 79.8];

% good profile
good25.N = 1:3;  good25.qber = [5.46 7.78 10.40];
good25.se = [0.36 0.42 0.48];  good25.rate = [53.7 42.5 37.0];
good10.N = 1:4;  good10.qber = [5.13 8.36 9.03 11.16];
good10.se = [0.69 0.87 0.91 0.99]; good10.rate = [96.1 87.6 81.1 78.8];

% modest profile (fails at N=1 at both spacings)
mod25.N = 1; mod25.qber = 11.70; mod25.se = 0.50; mod25.rate = 46.6;
mod10.N = 1; mod10.qber = 13.21; mod10.se = 1.06; mod10.rate = 86.1;

THRESH  = 11;                    % BB84 security threshold, %
SPACING = [10 25];               % km per hop

% colours (colourblind-safe, matches the 2D figures)
C.adv = [0.106 0.686 0.478];     % green
C.good= [0.165 0.471 0.839];     % blue
C.mod = [0.922 0.408 0.204];     % orange
GREY  = [0.55 0.55 0.52];

%% ------------------------------------------- figure 1: 3D ribbon of curves
figure('Name','QBER curves in 3D','Color','w','Position',[80 80 760 520]);
hold on; grid on; box on;

sets = { adv10, adv25; good10, good25; mod10, mod25 };
cols = { C.adv, C.good, C.mod };
names= { 'advanced', 'good', 'modest' };

for p = 1:3
    for s = 1:2
        d = sets{p,s};
        y = SPACING(s) * ones(size(d.N));
        plot3(d.N, y, d.qber, '-o', 'Color', cols{p}, ...
              'MarkerFaceColor', cols{p}, 'MarkerEdgeColor','w', ...
              'LineWidth', 2, 'MarkerSize', 5);
        % vertical 95% CI bars
        for k = 1:numel(d.N)
            plot3([d.N(k) d.N(k)], [y(k) y(k)], ...
                  d.qber(k) + 2*d.se(k)*[-1 1], '-', ...
                  'Color', cols{p}, 'LineWidth', 0.9);
        end
    end
end

% 11% threshold plane
[xx, yy] = meshgrid([0 15], [5 30]);
surf(xx, yy, THRESH*ones(size(xx)), 'FaceColor', GREY, ...
     'FaceAlpha', 0.16, 'EdgeColor', GREY, 'LineStyle','--');

xlabel('intermediate nodes  N'); ylabel('hop spacing  (km)');
zlabel('QBER  (%)');
title('Simulated QBER vs node count and hop spacing');
set(gca,'YTick',SPACING); xlim([0 15]); ylim([5 30]); zlim([0 15]);
view(-37.5, 22); legend(names,'Location','northwest'); legend boxoff;

%% ------------------------------------------ figure 2: interpolated surface
% Only the advanced profile has enough points for a surface.
figure('Name','QBER surface (advanced)','Color','w', ...
       'Position',[120 120 760 520]);
Ncom = 1:11;                               % N range common to both spacings
Z = [ adv10.qber(1:11) ; adv25.qber(1:11) ];
[Xq, Yq] = meshgrid(Ncom, linspace(10,25,40));
Zq = interp2([Ncom;Ncom], [10*ones(1,11); 25*ones(1,11)], Z, Xq, Yq, 'linear');

surf(Xq, Yq, Zq, 'EdgeColor','none', 'FaceAlpha', 0.95); hold on;
contour3(Xq, Yq, Zq, [THRESH THRESH], 'k-', 'LineWidth', 2);
colormap(parula); cb = colorbar; ylabel(cb,'QBER (%)');
xlabel('intermediate nodes  N'); ylabel('hop spacing  (km)');
zlabel('QBER  (%)');
title('QBER surface, advanced profile (black line = 11% threshold)');
view(-40, 28); grid on;

%% -------------------------------------------- figure 3: node ceilings bar3
figure('Name','Node ceiling','Color','w','Position',[160 160 700 500]);
ceilings = [0 3 10 ;    % 10 km : modest, good, advanced
            0 2 11];    % 25 km
b = bar3(ceilings);
try                                  % colour-by-height (MATLAB; skipped in Octave)
    for k = 1:numel(b)
        set(b(k),'CData',get(b(k),'ZData'),'FaceColor','interp');
    end
catch
end
set(gca,'XTickLabel',{'modest','good','advanced'}, ...
        'YTickLabel',{'10 km','25 km'});
xlabel('hardware profile'); ylabel('hop spacing'); zlabel('node ceiling  N');
title('Node ceiling (last N with 95% CI entirely below 11%)');
view(-50, 26); grid on;

%% --------------------------------- figure 4: QBER / rate joint trajectory
figure('Name','QBER and key rate','Color','w','Position',[200 200 760 520]);
hold on; grid on; box on;
plot3(adv25.N, adv25.rate, adv25.qber, '-o', 'Color', C.adv, ...
      'MarkerFaceColor', C.adv, 'MarkerEdgeColor','w', 'LineWidth', 2);
plot3(adv10.N, adv10.rate, adv10.qber, '-s', 'Color', C.adv, ...
      'MarkerFaceColor','w', 'LineWidth', 2);
xlabel('intermediate nodes  N'); ylabel('key rate  (bit s^{-1})');
zlabel('QBER  (%)');
title('Security and throughput together, advanced profile');
legend({'25 km spacing','10 km spacing'},'Location','northeast');
legend boxoff; view(-45, 20);

%% --------------------------------------------------------------- export
% print(1,'fig_qber_3d','-dpng','-r300');
% print(2,'fig_surface','-dpng','-r300');
