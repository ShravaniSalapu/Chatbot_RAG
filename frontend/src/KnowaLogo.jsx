function KnowaLogo({ showName = true }) {
  return (
    <div className="knowa-logo">
      <div className="logo-placeholder">
        K
      </div>

      {showName && (
        <span className="knowa-logo-name">
          KNOWA AI
        </span>
      )}
    </div>
  );
}

export default KnowaLogo;