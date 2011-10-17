module plot

  use constants
  use error,           only: fatal_error
  use geometry,        only: find_cell, dist_to_boundary, cross_surface, &
                             cross_lattice, cell_contains
  use geometry_header, only: Universe, BASE_UNIVERSE
  use global
  use particle_header, only: Particle, initialize_particle

  implicit none

contains

!===============================================================================
! RUN_PLOT
!===============================================================================

  subroutine run_plot()

    integer :: i              ! loop index
    integer :: surf           ! surface which particle is on
    integer :: last_cell      ! most recent cell particle was in
    real(8) :: coord(3)       ! starting coordinates
    real(8) :: last_x_coord   ! bounding x coordinate
    real(8) :: last_y_coord   ! bounding y coordinate
    real(8) :: d              ! distance to boundary
    real(8) :: distance       ! distance particle travels
    logical :: found_cell     ! found cell which particle is in?
    logical :: in_lattice     ! is surface crossing in lattice?
    character(MAX_LINE_LEN) :: msg   ! output/error message
    character(MAX_LINE_LEN) :: path_plot ! unit for binary plot file
    type(Cell),     pointer :: c    => null()
    type(Universe), pointer :: univ => null()
    type(Particle), pointer :: p    => null()

    ! Open plot file for binary writing
    path_plot = trim(path_input) // "plot.out"
    open(UNIT=UNIT_PLOT, FILE=path_plot, STATUS="replace", ACCESS="stream")

    ! Write origin, width, basis, and pixel width to file
    write(UNIT=UNIT_PLOT) plot_origin
    write(UNIT=UNIT_PLOT) plot_width
    write(UNIT=UNIT_PLOT) plot_basis
    write(UNIT=UNIT_PLOT) pixel

    ! Determine coordinates of the upper-left corner of the plot
    coord(1) = plot_origin(1) - plot_width(1) / 2.0
    coord(2) = plot_origin(2) + (plot_width(2) - pixel) / 2.0
    coord(3) = plot_origin(3)

    ! Determine bounding x and y coordinates for plot
    last_x_coord = plot_origin(1) + plot_width(1) / 2.0
    last_y_coord = plot_origin(2) - plot_width(2) / 2.0

    ! allocate and initialize particle
    allocate(p)

    ! loop over horizontal rays
    do while(coord(2) > last_y_coord)

       ! initialize the particle and set starting coordinate and direction
       call initialize_particle(p)
       p % xyz = coord
       p % xyz_local = coord
       p % uvw = (/ 1, 0, 0 /)

       ! write starting coordinate to file
       write(UNIT=UNIT_PLOT) p % xyz

       ! Find cell that particle is currently in
       univ => universes(BASE_UNIVERSE)
       call find_cell(univ, p, found_cell)

       ! =======================================================================
       ! MOVE PARTICLE FORWARD TO NEXT CELL

       if (.not. found_cell) then
          univ => universes(BASE_UNIVERSE)
          do i = 1, univ % n_cells
             p % xyz = coord
             p % xyz_local = coord
             p % cell = univ % cells(i)

             distance = INFINITY
             call dist_to_boundary(p, d, surf, in_lattice)
             if (d < distance) then
                ! Move particle forward to next surface
                p % xyz = p % xyz + d * p % uvw

                ! Check to make sure particle is actually going into this cell
                ! by moving it slightly forward and seeing if the cell contains
                ! that coordinate

                p % xyz = p % xyz + 1e-4 * p % uvw
                p % xyz_local = p % xyz

                c => cells(p % cell)
                if (.not. cell_contains(c, p)) cycle

                ! Reset coordinate to surface crossing
                p % xyz = p % xyz - 1e-4 * p % uvw
                p % xyz_local = p % xyz

                ! Set new distance and retain pointer to this cell
                distance = d
                last_cell = p % cell
             end if
          end do

          ! No cell was found on this horizontal ray
          if (distance == INFINITY) then
             p % xyz(1) = last_x_coord
             p % cell = 0
             write(UNIT_PLOT) p % xyz, p % cell

             ! Move to next horizontal ray
             coord(2) = coord(2) - pixel
             cycle
          end if

          ! Write coordinate where next cell begins
          write(UNIT=UNIT_PLOT) p % xyz, 0

          ! Process surface crossing for next cell
          p % cell = 0
          p % surface = -surf
          call cross_surface(p, last_cell)
       end if

       ! =======================================================================
       ! MOVE PARTICLE ACROSS HORIZONTAL TRACK

       do while (p % alive)

          ! Calculate distance to next boundary
          call dist_to_boundary(p, distance, surf, in_lattice)

          ! Advance particle
          p%xyz = p%xyz + distance * p%uvw
          p%xyz_local = p%xyz_local + distance * p%uvw

          ! If next boundary crossing is out of range of the plot, only include
          ! the visible portion and move to next horizontal ray
          if (p % xyz(1) >= last_x_coord) then
             p % alive = .false.
             p % xyz(1) = last_x_coord

             ! If there is no cell beyond this boundary, mark it as cell 0
             if (distance == INFINITY) p % cell = 0

             ! Write ending coordinates to file
             write(UNIT=UNIT_PLOT) p % xyz, p % cell
             cycle
          end if

          ! Write boundary crossing coordinates to file
          write(UNIT=UNIT_PLOT) p % xyz, p % cell

          last_cell = p % cell
          p % cell = 0
          if (in_lattice) then
             p % surface = 0
             call cross_lattice(p)
          else
             p % surface = surf
             call cross_surface(p, last_cell)

             ! Since boundary conditions are disabled in plotting mode, we need
             ! to manually add the last segment
             if (surfaces(surf) % bc == BC_VACUUM) then
                p % xyz(1) = last_x_coord
                write(UNIT=UNIT_PLOT) p % xyz, 0
                exit
             end if
          end if

       end do

       ! Move y-coordinate to next position
       coord(2) = coord(2) - pixel
    end do

    ! Close plot file
    close(UNIT=UNIT_PLOT)

  end subroutine run_plot

end module plot