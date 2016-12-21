const gulp = require( 'gulp' );
const zip = require( 'gulp-zip' );
const pkg = require( './package.json' );

gulp.task( 'default', () => {

    return gulp.src( 'src/**/*' )
        .pipe( zip( `io_scene_three-${pkg.version}.zip` ) )
        .pipe( gulp.dest( 'build' ) );

} );
